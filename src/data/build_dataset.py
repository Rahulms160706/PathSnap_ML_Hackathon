"""End-to-end Phase 1 feature dataset builder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.candidates.candidate_generator import generate_candidates
from src.data.preprocessing import TripData, align_reference_route, load_partition
from src.features.feature_extractor import extract_features


@dataclass
class PartitionData:
    features: pd.DataFrame
    labels: pd.DataFrame
    trip_stats: pd.DataFrame


def sample_observation_ids(trip: TripData, max_observations: int | None, seed: int) -> np.ndarray:
    ids = trip.track["observation_id"].to_numpy()
    if max_observations is None or len(ids) <= max_observations:
        return ids
    if max_observations < 2:
        raise ValueError("max_observations must be at least 2")
    sampled = np.linspace(0, len(ids) - 1, max_observations).round().astype(np.int64)
    return np.unique(ids[sampled])


def build_partition(
    root: str | Path,
    top_k: int,
    search_radius_m: float,
    cell_size_m: float,
    max_observations: int | None,
    seed: int,
    gap_threshold_s: float,
) -> PartitionData:
    trips = load_partition(root, gap_threshold_s)
    feature_frames: list[pd.DataFrame] = []
    label_frames: list[pd.DataFrame] = []
    stats_rows: list[dict[str, Any]] = []

    for trip in trips:
        labels = align_reference_route(trip)
        observation_ids = sample_observation_ids(trip, max_observations, seed)
        candidate_set = generate_candidates(trip, top_k, search_radius_m, cell_size_m, observation_ids)
        subset_labels = labels[labels["observation_id"].isin(observation_ids)].copy()
        features = extract_features(trip, candidate_set.candidates, subset_labels)
        if features.empty:
            raise RuntimeError(f"No candidate features generated for {trip.trip_id}")

        observations_with_positive = features.loc[features["is_reference"] == 1, "observation_id"].nunique()
        candidate_miss_rate = 1.0 - observations_with_positive / len(subset_labels)

        stats_rows.append(
            {
                "trip_id": trip.trip_id,
                "n_observations_total": trip.metadata["n_observations"],
                "n_observations_sampled": len(subset_labels),
                "n_route_arcs": trip.metadata["n_route_arcs"],
                "n_nodes": trip.metadata["n_nodes"],
                "n_arcs": trip.metadata["n_arcs"],
                "n_candidates": len(features),
                "mean_candidate_pool_size": candidate_set.stats["mean_candidate_pool_size"],
                "candidate_miss_rate": candidate_miss_rate,
                "route_continuous": trip.metadata["route_continuous"],
                "reference_distance_p95_m": float(subset_labels["reference_distance_m"].quantile(0.95)),
                "n_timestamp_gaps": trip.metadata["n_timestamp_gaps"],
            }
        )
        feature_frames.append(features)
        label_frames.append(subset_labels)

    return PartitionData(pd.concat(feature_frames, ignore_index=True), pd.concat(label_frames, ignore_index=True), pd.DataFrame(stats_rows))
