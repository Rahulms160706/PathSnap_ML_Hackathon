"""Feature selection fitted strictly on training folds."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.inspection import permutation_importance


@dataclass
class FeatureSelector:
    max_features: int = 10
    correlation_threshold: float = 0.97
    permutation_sample_size: int = 30_000
    random_state: int = 42
    selected_features_: list[str] = field(default_factory=list)
    dropped_features_: dict[str, list[str]] = field(default_factory=dict)
    importances_: dict[str, float] = field(default_factory=dict)

    def _prune_constant(self, frame: pd.DataFrame) -> list[str]:
        std = frame.std(numeric_only=True).replace(0, np.nan).fillna(0)
        keep = std[std > 1e-8].index.tolist()
        self.dropped_features_["constant"] = [c for c in frame.columns if c not in keep]
        return keep

    def _prune_correlated(self, frame: pd.DataFrame, columns: list[str]) -> list[str]:
        correlation = frame[columns].corr().abs().fillna(0)
        kept: list[str] = []
        for column in columns:
            redundant = any(correlation.loc[column, existing] > self.correlation_threshold for existing in kept)
            if not redundant:
                kept.append(column)
        self.dropped_features_["correlated"] = [c for c in columns if c not in kept]
        return kept

    def _importance_scores(self, frame: pd.DataFrame, y: np.ndarray, columns: list[str]) -> dict[str, float]:
        sample = frame[columns]
        target = y
        if len(sample) > self.permutation_sample_size:
            rng = np.random.default_rng(self.random_state)
            index = rng.choice(len(sample), self.permutation_sample_size, replace=False)
            sample = sample.iloc[index].reset_index(drop=True)
            target = target[index]

        model = ExtraTreesClassifier(
            n_estimators=80,
            min_samples_leaf=5,
            max_features="sqrt",
            n_jobs=1,
            random_state=self.random_state,
        )
        model.fit(sample, target)
        tree_score = dict(zip(columns, model.feature_importances_))

        permutation = permutation_importance(
            model,
            sample,
            target,
            n_repeats=2,
            random_state=self.random_state,
            scoring="f1",
            n_jobs=1,
        )
        permutation_score = dict(zip(columns, permutation.importances_mean))
        tree_rank = pd.Series(tree_score).rank(ascending=False, method="min")
        permutation_rank = pd.Series(permutation_score).rank(ascending=False, method="min")
        combined_rank = (tree_rank + permutation_rank) / 2.0
        combined = {
            column: {
                "tree_importance": float(tree_score[column]),
                "permutation_importance": float(permutation_score[column]),
                "combined_rank": float(combined_rank[column]),
            }
            for column in columns
        }
        self.importances_ = combined
        return {column: value["combined_rank"] for column, value in combined.items()}

    def fit(self, frame: pd.DataFrame, y: np.ndarray) -> "FeatureSelector":
        columns = self._prune_constant(frame)
        columns = self._prune_correlated(frame, columns)
        scores = self._importance_scores(frame, y, columns)
        ranked = sorted(columns, key=lambda column: scores[column])
        self.selected_features_ = ranked[: self.max_features]
        self.dropped_features_["importance"] = [c for c in columns if c not in self.selected_features_]
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame.loc[:, self.selected_features_].copy()

    def fit_transform(self, frame: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
        return self.fit(frame, y).transform(frame)

    def report(self) -> dict[str, object]:
        return {
            "selected_features": self.selected_features_,
            "dropped_features": self.dropped_features_,
            "importances": self.importances_,
        }
