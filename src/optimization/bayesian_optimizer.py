"""Bayesian hyperparameter optimisation for the saved PathSnap classifier."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

from src.evaluation.evaluate import candidate_metrics, observation_top1
from src.features.feature_extractor import FEATURE_COLUMNS
from src.models.feature_selection import FeatureSelector
from src.models.models import CandidateClassifier

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "experiments/results"
ARTIFACT_DIR = ROOT / "artifacts/model"
CONFIG_PATH = ROOT / "experiments/configs/bayesian_config.json"
PHASE1_CONFIG_PATH = ROOT / "experiments/configs/phase1_config.json"


def _native(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _load_features(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    compressed = Path(str(path) + ".gz")
    if compressed.exists():
        return pd.read_csv(compressed)
    raise FileNotFoundError(f"Missing feature file: {path} or {compressed}")


def _clean_features(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame.loc[:, columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)


class BayesianSearchSpace:
    def __init__(self, spec: dict[str, dict[str, Any]]):
        self.spec = spec
        self.names = list(spec)

    def encode(self, params: dict[str, Any]) -> np.ndarray:
        encoded = []
        for name in self.names:
            definition = self.spec[name]
            value = params[name]
            if definition["type"] == "log_uniform":
                low, high = np.log(definition["bounds"])
                encoded.append((np.log(float(value)) - low) / (high - low))
            elif definition["type"] == "integer":
                low, high = definition["bounds"]
                encoded.append((float(value) - low) / (high - low))
            else:
                choices = definition["choices"]
                encoded.append(float(choices.index(value)) / max(len(choices) - 1, 1))
        return np.clip(np.asarray(encoded, dtype=np.float64), 0.0, 1.0)

    def decode(self, encoded: np.ndarray) -> dict[str, Any]:
        encoded = np.clip(np.asarray(encoded, dtype=np.float64), 0.0, 1.0)
        decoded: dict[str, Any] = {}
        for index, name in enumerate(self.names):
            definition = self.spec[name]
            value = encoded[index]
            if definition["type"] == "log_uniform":
                low, high = np.log(definition["bounds"])
                decoded[name] = float(np.exp(low + value * (high - low)))
            elif definition["type"] == "integer":
                low, high = definition["bounds"]
                decoded[name] = int(round(low + value * (high - low)))
            else:
                choices = definition["choices"]
                decoded[name] = choices[int(round(value * (len(choices) - 1)))]
        return decoded


class BayesianOptimizer:
    def __init__(self, space: BayesianSearchSpace, objective: Callable[[dict[str, Any]], float], seed: int):
        self.space = space
        self.objective = objective
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.parameters: dict[str, Any] = {}
        self.scores: list[float] = []

    def _expected_improvement(self, model: GaussianProcessRegressor, candidates: np.ndarray, xi: float = 0.001) -> np.ndarray:
        mean, standard_deviation = model.predict(candidates, return_std=True)
        best = max(self.scores)
        improvement = mean - best - xi
        with np.errstate(divide="ignore", invalid="ignore"):
            z = improvement / standard_deviation
            acquisition = improvement * norm.cdf(z) + standard_deviation * norm.pdf(z)
        return np.where(standard_deviation > 1e-8, acquisition, 0.0)

    def _propose(self, n_initial_random: int) -> dict[str, Any]:
        dimension = len(self.space.names)
        if len(self.scores) < n_initial_random:
            encoded = self.rng.random(dimension)
        else:
            kernel = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
                length_scale=np.ones(dimension),
                length_scale_bounds=(1e-2, 1e2),
                nu=2.5,
            ) + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-6, 1e-1))
            model = GaussianProcessRegressor(kernel=kernel, normalize_y=True, random_state=self.seed)
            observed = np.vstack([self.space.encode(params) for params in self.parameters.values()])
            model.fit(observed, np.asarray(self.scores))
            candidates = self.rng.random((20_000, dimension))
            best_key = list(self.parameters.keys())[int(np.argmax(self.scores))]
            best_encoded = self.space.encode(self.parameters[best_key])
            candidates[:2_000] = np.clip(best_encoded + self.rng.normal(0, 0.08, (2_000, dimension)), 0, 1)
            acquisition = self._expected_improvement(model, candidates)
            encoded = candidates[int(np.argmax(acquisition))]
        return self.space.decode(encoded)

    def run(self, default_params: dict[str, Any], n_initial_random: int, n_total: int) -> tuple[dict[str, Any], float]:
        observations = {"default": default_params}
        for trial_number in range(1, n_total + 1):
            if trial_number == 1:
                params = dict(default_params)
            else:
                params = self._propose(n_initial_random)
            key = json.dumps(params, sort_keys=True)
            if key in observations:
                params = self._propose(n_initial_random + 1)
                key = json.dumps(params, sort_keys=True)
            score = self.objective(params)
            self.parameters[key] = params
            self.scores.append(score)
            observations[key] = params
            yield_trial = {"trial": trial_number, "params": params, "objective": score}
            yield yield_trial

    @property
    def best_params(self) -> dict[str, Any]:
        best_key = list(self.parameters.keys())[int(np.argmax(self.scores))]
        return self.parameters[best_key]

    @property
    def best_score(self) -> float:
        return max(self.scores)


def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []

    def logger(message: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {message}"
        print(line, flush=True)
        log_lines.append(line)

    config = json.loads(CONFIG_PATH.read_text())
    phase1_config = json.loads(PHASE1_CONFIG_PATH.read_text())
    metadata = json.loads((ARTIFACT_DIR / "metadata.json").read_text())
    selected_features = metadata["selected_features"]
    seed = int(config["seed"])

    train_features = _load_features(RESULTS_DIR / "train_features.csv")
    test_features = _load_features(RESULTS_DIR / "student_test_features.csv")
    x_train = _clean_features(train_features, selected_features)
    x_test = _clean_features(test_features, selected_features)
    y_train = train_features["is_reference"].to_numpy(dtype=np.int8)
    y_test = test_features["is_reference"].to_numpy(dtype=np.int8)
    groups = train_features["trip_id"].to_numpy()

    _, folds = _group_folds(train_features, config["n_splits"])
    logger(f"loaded {len(x_train)} train rows, {len(x_test)} student-test rows, {len(selected_features)} selected features")

    trial_rows: list[dict[str, Any]] = []

    def objective(params: dict[str, Any]) -> float:
        fold_scores: list[float] = []
        fold_times: list[float] = []
        for fold_number, (train_index, validation_index) in enumerate(folds, start=1):
            estimator = HistGradientBoostingClassifier(
                **{key: _native(value) for key, value in params.items()},
                random_state=seed,
            )
            start = time.perf_counter()
            estimator.fit(x_train.iloc[train_index], y_train[train_index])
            fold_times.append(time.perf_counter() - start)
            probability = estimator.predict_proba(x_train.iloc[validation_index])[:, 1]
            fold_scores.append(f1_score(y_train[validation_index], probability >= 0.5, average="macro", zero_division=0))
        row = {
            "params": json.dumps(params, sort_keys=True),
            "cv_macro_f1_mean": float(np.mean(fold_scores)),
            "cv_macro_f1_std": float(np.std(fold_scores, ddof=1)),
            "fit_seconds_mean": float(np.mean(fold_times)),
            "fold_scores": json.dumps([float(score) for score in fold_scores]),
        }
        trial_rows.append(row)
        return row["cv_macro_f1_mean"]

    space = BayesianSearchSpace(config["search_space"])
    optimizer = BayesianOptimizer(space, objective, seed)
    trial_records: list[dict[str, Any]] = []

    for trial in optimizer.run(config["default_params"], int(config["n_initial_random_trials"]), int(config["n_total_trials"])):
        trial_record = dict(trial)
        trial_record["rolling_best"] = max(record["objective"] for record in trial_records + [trial_record])
        trial_records.append(trial_record)
        logger(
            f"trial {trial['trial']:02d}: macro_f1={trial['objective']:.5f} "
            f"rolling_best={trial_record['rolling_best']:.5f} params={trial['params']}"
        )
        incremental_frame = pd.DataFrame(trial_rows)
        incremental_frame.insert(0, "trial", np.arange(1, len(incremental_frame) + 1))
        incremental_frame.insert(2, "rolling_best", [record["rolling_best"] for record in trial_records])
        incremental_frame.to_csv(RESULTS_DIR / "bayesian_trials.csv", index=False)

    trial_frame = pd.DataFrame(trial_rows)
    trial_frame.insert(0, "trial", np.arange(1, len(trial_frame) + 1))
    trial_frame.insert(2, "rolling_best", [record["rolling_best"] for record in trial_records])
    trial_frame.to_csv(RESULTS_DIR / "bayesian_trials.csv", index=False)

    best_params = optimizer.best_params
    best_score = optimizer.best_score
    (RESULTS_DIR / "bayesian_best_params.json").write_text(
        json.dumps({"best_params": best_params, "best_cv_macro_f1": best_score, "objective": config["objective"]}, indent=2)
    )
    logger(f"best trial: macro_f1={best_score:.5f} params={best_params}")

    final_params = {key: _native(value) for key, value in best_params.items()}
    start = time.perf_counter()
    estimator = HistGradientBoostingClassifier(**final_params, random_state=seed)
    estimator.fit(x_train, y_train)
    train_seconds = time.perf_counter() - start
    probability, inference_seconds = _predict(estimator, x_test)
    metrics = candidate_metrics(y_test, probability)
    top1 = observation_top1(test_features, probability)

    tuned_row = {
        "model": "hist_gradient_boosting",
        "variant": "bayesian_tuned",
        "cv_macro_f1": best_score,
        "test_macro_f1": metrics["candidate_macro_f1"],
        "test_observation_top1_accuracy": top1["observation_top1_accuracy"],
        "test_log_loss": metrics["log_loss"],
        "test_accuracy": metrics["candidate_accuracy"],
        "test_precision": metrics["candidate_precision"],
        "test_recall": metrics["candidate_recall"],
        "train_seconds": train_seconds,
        "inference_seconds": inference_seconds,
    }
    baseline = pd.read_csv(RESULTS_DIR / "model_comparison.csv")
    baseline_row = baseline[baseline["model"] == "hist_gradient_boosting"].iloc[0]
    untuned_row = {
        "model": "hist_gradient_boosting",
        "variant": "phase1_untuned",
        "cv_macro_f1": baseline_row["cv_macro_f1_mean"],
        "test_macro_f1": baseline_row["test_macro_f1"],
        "test_observation_top1_accuracy": baseline_row["test_observation_top1_accuracy"],
        "test_log_loss": baseline_row["test_log_loss"],
        "test_accuracy": baseline_row["test_accuracy"],
        "test_precision": baseline_row["test_precision"],
        "test_recall": baseline_row["test_recall"],
        "train_seconds": baseline_row["train_seconds"],
        "inference_seconds": baseline_row["inference_seconds"],
    }
    comparison = pd.DataFrame([untuned_row, tuned_row])
    comparison.to_csv(RESULTS_DIR / "bayesian_tuned_vs_untuned.csv", index=False)
    logger(f"tuned student test: top1={top1['observation_top1_accuracy']:.5f} macro_f1={metrics['candidate_macro_f1']:.5f} log_loss={metrics['log_loss']:.5f}")

    selector = FeatureSelector()
    selector.selected_features_ = list(selected_features)
    selector.dropped_features_ = {"constant": [], "correlated": [], "importance": [c for c in FEATURE_COLUMNS if c not in selected_features]}
    selector.importances_ = {}
    tuned_model = CandidateClassifier(estimator, selector=selector, name="hist_gradient_boosting_bayesian_tuned")
    tuned_model.feature_columns_ = list(FEATURE_COLUMNS)
    existing_metadata_path = ARTIFACT_DIR / "metadata.json"
    existing_metadata = json.loads(existing_metadata_path.read_text())
    baseline_model_path = ARTIFACT_DIR / "baseline_model.joblib"
    if "bayesian_tuned" not in str(existing_metadata.get("selected_model", "")):
        if not baseline_model_path.exists():
            shutil.copy2(ARTIFACT_DIR / "best_model.joblib", baseline_model_path)
        shutil.copy2(existing_metadata_path, ARTIFACT_DIR / "baseline_metadata.json")

    artifact_path = tuned_model.save(ARTIFACT_DIR / "tuned_model.joblib")

    tuned_metadata = {
        "model": "hist_gradient_boosting",
        "variant": "bayesian_tuned",
        "best_params": best_params,
        "best_cv_macro_f1": best_score,
        "feature_columns": list(FEATURE_COLUMNS),
        "selected_features": selected_features,
        "random_seed": seed,
        "phase1_config": phase1_config,
        "bayesian_config": config,
        "test_metrics": metrics,
        "observation_top1_accuracy": top1["observation_top1_accuracy"],
        "train_seconds": train_seconds,
        "inference_seconds": inference_seconds,
    }
    (ARTIFACT_DIR / "tuned_metadata.json").write_text(json.dumps(tuned_metadata, indent=2))

    tuned_model.save(ARTIFACT_DIR / "best_model.joblib")
    primary_metadata = dict(existing_metadata)
    primary_metadata.update(
        {
            "selected_model": tuned_model.name,
            "baseline_selected_model": existing_metadata.get("selected_model"),
            "variant": "bayesian_tuned",
            "bayesian_optimized": True,
            "best_params": best_params,
            "best_cv_macro_f1": best_score,
            "cv_macro_f1": best_score,
            "test_metrics": metrics,
            "observation_top1_accuracy": top1["observation_top1_accuracy"],
            "test_observation_top1": top1["observation_top1_accuracy"],
            "test_macro_f1": metrics["candidate_macro_f1"],
            "test_log_loss": metrics["log_loss"],
            "train_seconds": train_seconds,
            "inference_seconds": inference_seconds,
        }
    )
    existing_metadata_path.write_text(json.dumps(primary_metadata, indent=2))
    logger(f"promoted Bayesian-tuned model to primary artifact: {ARTIFACT_DIR / 'best_model.joblib'}")

    reloaded = CandidateClassifier.load(artifact_path)
    reload_probabilities = reloaded.predict_proba(test_features.head(100))
    reload_check = {
        "reloaded_model": reloaded.name,
        "prediction_shape": list(reload_probabilities.shape),
        "probability_min": float(reload_probabilities.min()),
        "probability_max": float(reload_probabilities.max()),
        "all_in_unit_interval": bool(((reload_probabilities >= 0) & (reload_probabilities <= 1)).all()),
    }
    (RESULTS_DIR / "bayesian_reload_verification.json").write_text(json.dumps(reload_check, indent=2))
    logger(f"reload verification: {reload_check}")

    _plot_trials(trial_frame)
    _plot_comparison(comparison)
    (RESULTS_DIR / "bayesian_optimization_log.txt").write_text("\n".join(log_lines) + "\n")
    (RESULTS_DIR / "bayesian_optimization_summary.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "n_trials": len(trial_frame),
                "best_params": best_params,
                "best_cv_macro_f1": best_score,
                "tuned_test": tuned_row,
                "promoted_to_best_model": True,
                "primary_metadata": primary_metadata,
                "reload_check": reload_check,
            },
            indent=2,
        )
    )


def _group_folds(features: pd.DataFrame, n_splits: int) -> tuple[np.ndarray, list[tuple[np.ndarray, np.ndarray]]]:
    groups = features["trip_id"].to_numpy()
    splitter = GroupKFold(n_splits=n_splits)
    return np.unique(groups), list(splitter.split(np.zeros(len(groups)), groups=groups))


def _predict(estimator: HistGradientBoostingClassifier, features: pd.DataFrame) -> tuple[np.ndarray, float]:
    import time

    start = time.perf_counter()
    probability = estimator.predict_proba(features)[:, 1]
    return probability, time.perf_counter() - start


def _plot_trials(frame: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(frame["trial"], frame["cv_macro_f1_mean"], marker="o", label="trial")
    ax.plot(frame["trial"], frame["rolling_best"], marker="", linestyle="--", label="rolling best")
    ax.set_title("Bayesian Optimisation Trials")
    ax.set_xlabel("trial")
    ax.set_ylabel("group CV macro F1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ROOT / "report/figures/bayesian_trials.png", dpi=150)
    plt.close(fig)


def _plot_comparison(frame: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = ["cv_macro_f1", "test_macro_f1", "test_observation_top1_accuracy"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for ax, metric in zip(axes, metrics):
        ax.bar(frame["variant"], frame[metric], color=["#94a3b8", "#2563eb"])
        ax.set_title(metric)
        ax.tick_params(axis="x", rotation=15)
        for index, value in enumerate(frame[metric]):
            ax.text(index, value, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "report/figures/bayesian_tuned_vs_untuned.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    run()
