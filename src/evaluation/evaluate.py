"""Candidate-level and observation-level evaluation utilities."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, log_loss, precision_score, recall_score


def candidate_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predictions = (probabilities >= 0.5).astype(np.int8)
    clipped = np.clip(probabilities, 1e-12, 1 - 1e-12)
    return {
        "candidate_accuracy": float(accuracy_score(y_true, predictions)),
        "candidate_precision": float(precision_score(y_true, predictions, zero_division=0)),
        "candidate_recall": float(recall_score(y_true, predictions, zero_division=0)),
        "candidate_f1": float(f1_score(y_true, predictions, zero_division=0)),
        "candidate_macro_f1": float(f1_score(y_true, predictions, average="macro", zero_division=0)),
        "log_loss": float(log_loss(y_true, clipped, labels=[0, 1])),
    }


def observation_top1(features: pd.DataFrame, probabilities: np.ndarray) -> dict[str, float]:
    required = {"trip_id", "observation_id", "candidate_arc_id", "reference_arc_id", "candidate_rank"}
    if not required.issubset(features.columns):
        return {"observation_top1_accuracy": np.nan, "n_observations": np.nan, "candidate_miss_rate": np.nan}

    scored = features.loc[:, list(required)].copy()
    scored["candidate_probability"] = probabilities
    scored = scored.sort_values(["trip_id", "observation_id", "candidate_probability", "candidate_rank"], ascending=[True, True, False, True])
    best = scored.drop_duplicates(["trip_id", "observation_id"], keep="first")
    return {
        "observation_top1_accuracy": float((best["candidate_arc_id"] == best["reference_arc_id"]).mean()),
        "n_observations": int(len(best)),
    }


def candidate_miss_rate(features: pd.DataFrame) -> float:
    if "is_reference" not in features.columns:
        return np.nan
    grouped = features.groupby(["trip_id", "observation_id"], sort=False)["is_reference"].max()
    return float(1.0 - grouped.mean())


def make_group_folds(features: pd.DataFrame, n_splits: int, seed: int) -> tuple[np.ndarray, list[tuple[np.ndarray, np.ndarray]]]:
    from sklearn.model_selection import GroupKFold

    groups = features["trip_id"].to_numpy()
    unique_groups = np.unique(groups)
    if n_splits > len(unique_groups):
        raise ValueError("n_splits exceeds number of trips")
    splitter = GroupKFold(n_splits=n_splits)
    folds = list(splitter.split(np.zeros(len(groups)), groups=groups))
    del seed
    return unique_groups, folds


def time_inference(model: Any, features: pd.DataFrame) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    probabilities = model.predict_proba(features)
    return probabilities, time.perf_counter() - start


def mean_std(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, dict[str, float]]:
    frame = pd.DataFrame(rows)
    return {
        column: {"mean": float(frame[column].mean()), "std": float(frame[column].std(ddof=1))}
        for column in columns
        if column in frame.columns
    }
