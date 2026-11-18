"""Spatial candidate generation using a projected-coordinate spatial hash."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from src.data.preprocessing import TripData, local_projection, point_segment_distance_m


@dataclass
class CandidateSet:
    candidates: pd.DataFrame
    stats: dict[str, float]


class SegmentGridIndex:
    def __init__(self, seg_a: np.ndarray, seg_b: np.ndarray, cell_size_m: float):
        self.seg_a = seg_a
        self.seg_b = seg_b
        self.cell_size = cell_size_m
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        lower = np.minimum(seg_a, seg_b)
        upper = np.maximum(seg_a, seg_b)
        min_cell = np.floor(lower / cell_size_m).astype(np.int64)
        max_cell = np.floor(upper / cell_size_m).astype(np.int64)
        for arc_id, (x0, y0, x1, y1) in enumerate(zip(min_cell[:, 0], min_cell[:, 1], max_cell[:, 0], max_cell[:, 1])):
            for cell_x in range(x0, x1 + 1):
                for cell_y in range(y0, y1 + 1):
                    self.cells[(cell_x, cell_y)].append(arc_id)
        self.midpoints = (seg_a + seg_b) / 2.0
        self.midpoint_tree = cKDTree(self.midpoints)

    def query(self, points: np.ndarray, radius_m: float, top_k: int) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
        radius_cells = int(np.ceil(radius_m / self.cell_size))
        distances = np.full((len(points), top_k), np.inf, dtype=np.float64)
        arc_ids = np.full((len(points), top_k), -1, dtype=np.int64)
        all_indices: list[np.ndarray] = []

        for obs_id, point in enumerate(points):
            cell_x = int(np.floor(point[0] / self.cell_size))
            cell_y = int(np.floor(point[1] / self.cell_size))
            chunk: list[int] = []
            for dx in range(-radius_cells, radius_cells + 1):
                for dy in range(-radius_cells, radius_cells + 1):
                    chunk.extend(self.cells.get((cell_x + dx, cell_y + dy), ()))
            if not chunk:
                fallback = self.midpoint_tree.query(point, k=min(top_k, len(self.midpoints)))[1]
                chunk = np.atleast_1d(fallback).tolist()
            indices = np.unique(np.asarray(chunk, dtype=np.int64))
            all_indices.append(indices)
            candidate_distance, _ = point_segment_distance_m(point[None, :], self.seg_a[indices], self.seg_b[indices])
            candidate_distance = candidate_distance.ravel()
            keep = min(top_k, len(indices))
            if keep == 0:
                continue
            if keep == len(indices):
                order = np.argsort(candidate_distance)
            else:
                order = np.argpartition(candidate_distance, keep - 1)[:keep]
                order = order[np.argsort(candidate_distance[order])]
            distances[obs_id, :keep] = candidate_distance[order]
            arc_ids[obs_id, :keep] = indices[order]

        return distances, arc_ids, all_indices


def generate_candidates(
    trip: TripData,
    top_k: int = 8,
    search_radius_m: float = 80.0,
    cell_size_m: float = 50.0,
    observation_ids: np.ndarray | None = None,
) -> CandidateSet:
    latitude0 = float(trip.track["latitude"].mean())
    node_xy = local_projection(trip.nodes["longitude"].to_numpy(), trip.nodes["latitude"].to_numpy(), latitude0)
    from_node = trip.arcs["from_node_id"].to_numpy()
    to_node = trip.arcs["to_node_id"].to_numpy()
    seg_a = node_xy[from_node]
    seg_b = node_xy[to_node]

    track = trip.track
    if observation_ids is not None:
        track = track[track["observation_id"].isin(observation_ids)].copy()
    points = local_projection(track["longitude"].to_numpy(), track["latitude"].to_numpy(), latitude0)

    index = SegmentGridIndex(seg_a, seg_b, cell_size_m)
    distances, arc_ids, candidate_indices = index.query(points, search_radius_m, top_k)

    rows: list[pd.DataFrame] = []
    for row_id, (_, track_row) in enumerate(track.iterrows()):
        valid = arc_ids[row_id] >= 0
        n_valid = int(valid.sum())
        if n_valid == 0:
            continue
        rows.append(
            pd.DataFrame(
                {
                    "trip_id": trip.trip_id,
                    "observation_id": int(track_row["observation_id"]),
                    "candidate_arc_id": arc_ids[row_id, valid],
                    "candidate_distance": distances[row_id, valid],
                    "candidate_rank": np.arange(1, n_valid + 1, dtype=np.int16),
                    "candidate_pool_size": len(candidate_indices[row_id]),
                }
            )
        )

    candidates = pd.concat(rows, ignore_index=True)
    stats = {
        "n_observations": len(track),
        "n_candidates": len(candidates),
        "mean_candidate_pool_size": float(np.mean([len(x) for x in candidate_indices])),
        "max_candidate_pool_size": float(np.max([len(x) for x in candidate_indices])),
    }
    return CandidateSet(candidates, stats)
