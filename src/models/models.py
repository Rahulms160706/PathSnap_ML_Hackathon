"""Common candidate-classification model interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.feature_selection import FeatureSelector

POSITIVE_LABEL = 1


class CandidateClassifier:
    """Wraps a selector and estimator while preserving candidate-row identity."""

    def __init__(self, estimator: Any, selector: FeatureSelector | None = None, name: str = "model"):
        self.estimator = estimator
        self.selector = selector
        self.name = name
        self.feature_columns_: list[str] = []

    def fit(self, features: pd.DataFrame, y: np.ndarray) -> "CandidateClassifier":
        self.feature_columns_ = list(features.columns)
        if self.selector is not None:
            x = self.selector.fit_transform(features, y)
        else:
            x = features.copy()
        self.estimator.fit(x, y)
        return self

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        x = self._prepare(features)
        probabilities = self.estimator.predict_proba(self._estimator_input(x))
        positive_index = np.where(self.estimator.classes_ == POSITIVE_LABEL)[0]
        if len(positive_index) != 1:
            raise RuntimeError("Binary positive class is unavailable")
        return probabilities[:, positive_index[0]]

    def predict(self, features: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(features) >= threshold).astype(np.int8)

    def _prepare(self, features: pd.DataFrame) -> pd.DataFrame:
        missing = [column for column in self.feature_columns_ if column not in features.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")
        if self.selector is not None:
            return self.selector.transform(features.loc[:, self.feature_columns_])
        return features.loc[:, self.feature_columns_].copy()

    def _estimator_input(self, features: pd.DataFrame) -> pd.DataFrame | np.ndarray:
        names = getattr(self.estimator, "feature_names_in_", None)
        if names is None or not set(map(str, names)).issubset(features.columns):
            return features.to_numpy()
        return features.loc[:, list(names)]

    def predict_candidates(self, features: pd.DataFrame) -> pd.DataFrame:
        identifier_columns = [column for column in ("trip_id", "observation_id", "candidate_arc_id", "candidate_rank") if column in features.columns]
        output = features.loc[:, identifier_columns].copy()
        output["candidate_probability"] = self.predict_proba(features)
        output["model_name"] = self.name
        return output

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "CandidateClassifier":
        return joblib.load(Path(path))


def build_model(name: str, random_state: int = 42, use_selection: bool = True) -> CandidateClassifier:
    selector = FeatureSelector(random_state=random_state) if use_selection else None
    estimators: dict[str, Any] = {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(max_iter=1_000, class_weight="balanced", random_state=random_state)),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=120,
            min_samples_leaf=3,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=1,
            random_state=random_state,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=120,
            min_samples_leaf=3,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=1,
            random_state=random_state,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=120,
            learning_rate=0.1,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            random_state=random_state,
        ),
        "knn": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("classifier", KNeighborsClassifier(n_neighbors=15, weights="distance", n_jobs=1)),
            ]
        ),
    }
    if name not in estimators:
        raise KeyError(name)
    return CandidateClassifier(estimators[name], selector=selector, name=name)


MODEL_NAMES = [
    "logistic_regression",
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
    "knn",
]
