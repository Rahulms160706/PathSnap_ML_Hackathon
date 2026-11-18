"""Candidate-road-segment feature construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.preprocessing import TripData, local_projection

FEATURE_COLUMNS = [
    "candidate_distance_m",
    "candidate_rank",
    "candidate_pool_size",
    "projection_ratio",
    "distance_length_ratio",
    "segment_length_m",
    "gps_speed_mps",
    "gps_heading_sin",
    "gps_heading_cos",
    "segment_heading_diff_rad",
    "reverse_heading_diff_rad",
    "min_heading_diff_rad",
    "previous_gps_distance_m",
    "transition_distance_m",
    "transition_ratio",
    "endpoint_degree_sum",
    "dt_s",
    "gap_flag",
]


def _heading(dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    return np.arctan2(dx, dy)


def _angle_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.abs(np.arctan2(np.sin(a - b), np.cos(a - b)))


def extract_features(
    trip: TripData,
    candidates: pd.DataFrame,
    labels: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame()

    track = trip.track.sort_values("observation_id").reset_index(drop=True)
    obs_index = pd.Series(np.arange(len(track), dtype=np.int64), index=track["observation_id"].to_numpy())
    latitude0 = float(track["latitude"].mean())
    points = local_projection(track["longitude"].to_numpy(), track["latitude"].to_numpy(), latitude0)

    dx = np.diff(points[:, 0], prepend=points[0, 0])
    dy = np.diff(points[:, 1], prepend=points[0, 1])
    gps_heading = _heading(dx, dy)
    gps_speed = np.hypot(dx, dy) / np.maximum(track["dt_s"].to_numpy(), 1e-6)
    previous_distance = np.hypot(dx, dy)

    node_xy = local_projection(trip.nodes["longitude"].to_numpy(), trip.nodes["latitude"].to_numpy(), latitude0)
    arcs = trip.arcs
    from_node = arcs["from_node_id"].to_numpy()
    to_node = arcs["to_node_id"].to_numpy()
    seg_a = node_xy[from_node]
    seg_b = node_xy[to_node]
    segment_vector = seg_b - seg_a
    segment_length = np.linalg.norm(segment_vector, axis=1)
    segment_heading = _heading(segment_vector[:, 0], segment_vector[:, 1])

    degree = np.bincount(np.concatenate([from_node, to_node]), minlength=len(node_xy))

    observation_ids = candidates["observation_id"].to_numpy()
    arc_ids = candidates["candidate_arc_id"].to_numpy()
    obs_rows = obs_index.loc[observation_ids].to_numpy()

    candidate_points = points[obs_rows]
    candidate_a = seg_a[arc_ids]
    candidate_b = seg_b[arc_ids]
    candidate_ab = candidate_b - candidate_a
    denominator = np.einsum("ij,ij->i", candidate_ab, candidate_ab)
    projection = np.clip(
        np.einsum("ij,ij->i", candidate_points - candidate_a, candidate_ab) / np.maximum(denominator, 1e-12),
        0.0,
        1.0,
    )
    closest = candidate_a + projection[:, None] * candidate_ab
    distance = np.linalg.norm(candidate_points - closest, axis=1)

    candidate_length = segment_length[arc_ids]
    candidate_heading = segment_heading[arc_ids]
    previous_points = points[np.maximum(obs_rows - 1, 0)]

    frame = candidates.copy()
    frame["candidate_distance_m"] = distance.ravel()
    frame["projection_ratio"] = projection.ravel()
    frame["distance_length_ratio"] = frame["candidate_distance_m"] / np.maximum(candidate_length, 1e-6)
    frame["segment_length_m"] = candidate_length
    frame["gps_speed_mps"] = gps_speed[obs_rows]
    frame["gps_heading_sin"] = np.sin(gps_heading[obs_rows])
    frame["gps_heading_cos"] = np.cos(gps_heading[obs_rows])
    frame["segment_heading_diff_rad"] = _angle_difference(gps_heading[obs_rows], candidate_heading)
    frame["reverse_heading_diff_rad"] = _angle_difference(gps_heading[obs_rows], candidate_heading + np.pi)
    frame["min_heading_diff_rad"] = np.minimum(frame["segment_heading_diff_rad"], frame["reverse_heading_diff_rad"])
    frame["previous_gps_distance_m"] = previous_distance[obs_rows]
    frame["transition_distance_m"] = np.linalg.norm(previous_points - closest, axis=1)
    frame["transition_ratio"] = frame["transition_distance_m"] / np.maximum(candidate_length, 1e-6)
    frame["endpoint_degree_sum"] = degree[from_node[arc_ids]] + degree[to_node[arc_ids]]
    frame["dt_s"] = track["dt_s"].to_numpy()[obs_rows]
    frame["gap_flag"] = track["gap_flag"].to_numpy()[obs_rows]

    if labels is not None:
        frame = frame.merge(
            labels[["trip_id", "observation_id", "reference_arc_id", "reference_distance_m"]],
            on=["trip_id", "observation_id"],
            how="left",
            validate="many_to_one",
        )
        frame["is_reference"] = (frame["candidate_arc_id"] == frame["reference_arc_id"]).astype(np.int8)

    return frame
