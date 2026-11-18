"""Trip loading, validation, projection and reference-route alignment."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


@dataclass
class TripData:
    trip_id: str
    track: pd.DataFrame
    nodes: pd.DataFrame
    arcs: pd.DataFrame
    route: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


def discover_trip_dirs(root: str | Path) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    return sorted(path for path in root.iterdir() if path.is_dir() and _has_required_files(path))


def _has_required_files(path: Path) -> bool:
    return all((path / f"{path.name}.{ext}").is_file() for ext in ("track", "nodes", "arcs", "route"))


def _load_numeric(path: Path, expected_columns: int) -> np.ndarray:
    array = np.loadtxt(path, dtype=np.float64, ndmin=2)
    if array.ndim != 2 or array.shape[1] != expected_columns:
        raise ValueError(f"Invalid shape {array.shape} in {path}; expected {expected_columns} columns")
    if not np.isfinite(array).all():
        raise ValueError(f"Non-finite values found in {path}")
    return array


def load_trip(trip_dir: str | Path, gap_threshold_s: float = 10.0) -> TripData:
    trip_dir = Path(trip_dir)
    trip_id = trip_dir.name

    raw_track = _load_numeric(trip_dir / f"{trip_id}.track", 3)
    raw_nodes = _load_numeric(trip_dir / f"{trip_id}.nodes", 2)
    raw_arcs = _load_numeric(trip_dir / f"{trip_id}.arcs", 2)
    raw_route = _load_numeric(trip_dir / f"{trip_id}.route", 1).ravel()

    raw_arcs_int = np.rint(raw_arcs).astype(np.int64)
    route = np.rint(raw_route).astype(np.int64)

    if not np.allclose(raw_arcs, raw_arcs_int):
        raise ValueError(f"Non-integer arc endpoints in {trip_id}")
    if not np.allclose(raw_route, route):
        raise ValueError(f"Non-integer route IDs in {trip_id}")

    longitude, latitude, timestamp = raw_track.T
    if not ((-180 <= longitude) & (longitude <= 180)).all():
        raise ValueError(f"Longitude out of range in {trip_id}")
    if not ((-90 <= latitude) & (latitude <= 90)).all():
        raise ValueError(f"Latitude out of range in {trip_id}")
    if not ((longitude != 0) | (latitude != 0)).all():
        raise ValueError(f"Null-island coordinates in {trip_id}")

    dt = np.diff(timestamp, prepend=timestamp[0])
    non_positive = int(np.sum(dt[1:] <= 0))
    if non_positive:
        raise ValueError(f"Timestamps are not strictly increasing in {trip_id}: {non_positive} violations")

    if not ((-180 <= raw_nodes[:, 0]) & (raw_nodes[:, 0] <= 180)).all():
        raise ValueError(f"Node longitude out of range in {trip_id}")
    if not ((raw_arcs_int >= 0).all() and (raw_arcs_int < len(raw_nodes)).all()):
        raise ValueError(f"Invalid arc endpoint in {trip_id}")
    if not ((route >= 0).all() and (route < len(raw_arcs_int)).all()):
        raise ValueError(f"Invalid reference route arc ID in {trip_id}")

    track = pd.DataFrame(
        {
            "trip_id": trip_id,
            "observation_id": np.arange(len(raw_track), dtype=np.int64),
            "longitude": longitude,
            "latitude": latitude,
            "timestamp_s": timestamp,
            "dt_s": dt,
            "gap_flag": (dt > gap_threshold_s).astype(np.int8),
        }
    )
    nodes = pd.DataFrame(raw_nodes, columns=["longitude", "latitude"])
    nodes.index.name = "node_id"
    arcs = pd.DataFrame(raw_arcs_int, columns=["from_node_id", "to_node_id"])
    arcs.index.name = "arc_id"

    metadata = {
        "n_observations": len(track),
        "n_nodes": len(nodes),
        "n_arcs": len(arcs),
        "n_route_arcs": len(route),
        "n_timestamp_gaps": int(track["gap_flag"].sum()),
        "max_timestamp_gap_s": float(dt.max()),
        "duration_s": float(timestamp[-1] - timestamp[0]),
        "bbox": [
            float(longitude.min()),
            float(latitude.min()),
            float(longitude.max()),
            float(latitude.max()),
        ],
        "route_continuous": bool(
            np.all(
                (raw_arcs_int[route[:-1], 1] == raw_arcs_int[route[1:], 0])
                | (raw_arcs_int[route[:-1], 0] == raw_arcs_int[route[1:], 1])
            )
        ),
    }
    return TripData(trip_id, track, nodes, arcs, route, metadata)


def load_partition(root: str | Path, gap_threshold_s: float = 10.0) -> list[TripData]:
    return [load_trip(path, gap_threshold_s) for path in discover_trip_dirs(root)]


def local_projection(longitude: np.ndarray, latitude: np.ndarray, latitude0: float) -> np.ndarray:
    scale_x = 111_320.0 * np.cos(np.deg2rad(latitude0))
    scale_y = 111_320.0
    return np.column_stack([np.asarray(longitude) * scale_x, np.asarray(latitude) * scale_y])


def point_segment_distance_m(points: np.ndarray, seg_a: np.ndarray, seg_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ab = seg_b - seg_a
    denom = np.einsum("ij,ij->i", ab, ab)
    safe_denom = np.where(denom > 0, denom, 1.0)
    ap = points[:, None, :] - seg_a[None, :, :]
    projection = np.clip(np.einsum("nij,ij->ni", ap, ab) / safe_denom[None, :], 0.0, 1.0)
    closest = seg_a[None, :, :] + projection[:, :, None] * ab[None, :, :]
    distance = np.linalg.norm(points[:, None, :] - closest, axis=2)
    return distance, projection


def align_reference_route(trip: TripData, chunk_size: int = 512) -> pd.DataFrame:
    """Align GPS observations to the chronological reference route.

    Each observation is first associated with its nearest reference-arc geometry.
    Those raw indices are then regularised with weighted isotonic regression, which
    enforces the known chronological ordering of the reference route while using
    spatial confidence as the observation weight. No candidate model is involved.
    """
    latitude0 = float(trip.track["latitude"].mean())
    points = local_projection(trip.track["longitude"].to_numpy(), trip.track["latitude"].to_numpy(), latitude0)
    route_arcs = trip.route
    node_xy = local_projection(trip.nodes["longitude"].to_numpy(), trip.nodes["latitude"].to_numpy(), latitude0)
    seg_a = node_xy[trip.arcs["from_node_id"].to_numpy()[route_arcs]]
    seg_b = node_xy[trip.arcs["to_node_id"].to_numpy()[route_arcs]]

    nearest_idx = np.empty(len(points), dtype=np.int64)
    nearest_distance = np.empty(len(points), dtype=np.float64)
    for start in range(0, len(points), chunk_size):
        stop = min(start + chunk_size, len(points))
        distance, _ = point_segment_distance_m(points[start:stop], seg_a, seg_b)
        nearest_idx[start:stop] = distance.argmin(axis=1)
        nearest_distance[start:stop] = distance.min(axis=1)

    observations = np.arange(len(points), dtype=np.float64)
    weight = 1.0 / np.maximum(nearest_distance, 1.0)
    aligned = IsotonicRegression(increasing=True, out_of_bounds="clip").fit_transform(
        observations, nearest_idx.astype(np.float64), sample_weight=weight
    )
    aligned_idx = np.clip(np.rint(aligned).astype(np.int64), 0, len(route_arcs) - 1)

    return pd.DataFrame(
        {
            "trip_id": trip.trip_id,
            "observation_id": np.arange(len(points), dtype=np.int64),
            "reference_arc_id": route_arcs[aligned_idx],
            "reference_route_position": aligned_idx,
            "raw_nearest_route_position": nearest_idx,
            "reference_distance_m": nearest_distance,
        }
    )
