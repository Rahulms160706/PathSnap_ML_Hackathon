"""Phase 1 end-to-end training, evaluation and artifact generation."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.build_dataset import build_partition
from src.evaluation.evaluate import candidate_metrics, candidate_miss_rate, make_group_folds, observation_top1
from src.features.feature_extractor import FEATURE_COLUMNS
from src.models.feature_selection import FeatureSelector
from src.models.models import MODEL_NAMES, CandidateClassifier, build_model

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "experiments/configs/phase1_config.json"
RESULTS_DIR = ROOT / "experiments/results"
FIGURE_DIR = ROOT / "report/figures"
ARTIFACT_DIR = ROOT / "artifacts/model"


def _clean_features(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame.loc[:, FEATURE_COLUMNS].copy()
    return features.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _cv_fold_rows(
    train_features: pd.DataFrame,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    config: dict[str, Any],
    logger,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    selectors: list[FeatureSelector] = []
    x_all = _clean_features(train_features)

    for fold_number, (train_index, validation_index) in enumerate(folds, start=1):
        fold_x = x_all.iloc[train_index]
        fold_y = y[train_index]
        selector = FeatureSelector(
            max_features=config["max_features"],
            correlation_threshold=config["correlation_threshold"],
            permutation_sample_size=config["permutation_sample_size"],
            random_state=config["seed"] + fold_number,
        )
        selector.fit(fold_x, fold_y)
        selectors.append(selector)
        x_train = selector.transform(fold_x)
        x_validation = selector.transform(x_all.iloc[validation_index])
        logger(f"fold {fold_number}: selected {len(selector.selected_features_)} features")

        for model_name in config["model_names"]:
            model = build_model(model_name, config["seed"], use_selection=False)
            start = time.perf_counter()
            model.fit(x_train, fold_y)
            train_seconds = time.perf_counter() - start
            probabilities, inference_seconds = _predict(model, x_validation)
            metrics = candidate_metrics(y[validation_index], probabilities)
            rows.append(
                {
                    "model": model_name,
                    "fold": fold_number,
                    "n_train_rows": len(train_index),
                    "n_validation_rows": len(validation_index),
                    "train_seconds": train_seconds,
                    "inference_seconds": inference_seconds,
                    **metrics,
                }
            )
            logger(f"  {model_name}: macro_f1={metrics['candidate_macro_f1']:.4f} time={train_seconds:.2f}s")

    return pd.DataFrame(rows), selectors


def _initial_feature_ablation(
    train_features: pd.DataFrame,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    config: dict[str, Any],
    logger,
) -> pd.DataFrame:
    x_all = _clean_features(train_features)
    rows: list[dict[str, Any]] = []
    for model_name in ["logistic_regression", "extra_trees"]:
        for fold_number, (train_index, validation_index) in enumerate(folds, start=1):
            model = build_model(model_name, config["seed"], use_selection=False)
            start = time.perf_counter()
            model.fit(x_all.iloc[train_index], y[train_index])
            train_seconds = time.perf_counter() - start
            probabilities, inference_seconds = _predict(model, x_all.iloc[validation_index])
            metrics = candidate_metrics(y[validation_index], probabilities)
            rows.append(
                {
                    "model": model_name,
                    "fold": fold_number,
                    "feature_set": "initial",
                    "train_seconds": train_seconds,
                    "inference_seconds": inference_seconds,
                    **metrics,
                }
            )
        logger(f"initial-feature ablation complete for {model_name}")
    return pd.DataFrame(rows)


def _predict(model: CandidateClassifier, features: pd.DataFrame) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    probabilities = model.predict_proba(features)
    return probabilities, time.perf_counter() - start


def _plot_comparison(frame: pd.DataFrame, column: str, title: str, filename: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8))
    aggregated = frame.groupby("model")[column].mean().sort_values()
    ax.barh(aggregated.index, aggregated.to_numpy(), color="#3b82f6")
    ax.set_title(title)
    ax.set_xlabel(ylabel)
    for index, value in enumerate(aggregated.to_numpy()):
        ax.text(value, index, f" {value:.4f}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / filename, dpi=150)
    plt.close(fig)


def run() -> None:
    for directory in (RESULTS_DIR, FIGURE_DIR, ARTIFACT_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    log_lines: list[str] = []

    def logger(message: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {message}"
        print(line, flush=True)
        log_lines.append(line)

    config = json.loads(CONFIG_PATH.read_text())
    logger("phase 1 pipeline started")

    train = build_partition(
        ROOT / "data/train",
        config["top_k"],
        config["search_radius_m"],
        config["cell_size_m"],
        config["max_train_observations_per_trip"],
        config["seed"],
        config["gap_threshold_s"],
    )
    logger(f"training features: {train.features.shape}")

    test = build_partition(
        ROOT / "data/student_test",
        config["top_k"],
        config["search_radius_m"],
        config["cell_size_m"],
        config["max_test_observations_per_trip"],
        config["seed"],
        config["gap_threshold_s"],
    )
    logger(f"student-test features: {test.features.shape}")

    train.trip_stats.to_csv(RESULTS_DIR / "train_trip_stats.csv", index=False)
    test.trip_stats.to_csv(RESULTS_DIR / "student_test_trip_stats.csv", index=False)
    train.features.to_csv(RESULTS_DIR / "train_features.csv", index=False)
    test.features.to_csv(RESULTS_DIR / "student_test_features.csv", index=False)

    overall_candidate_miss = candidate_miss_rate(train.features)
    test_candidate_miss = candidate_miss_rate(test.features)
    x_train = _clean_features(train.features)
    x_test = _clean_features(test.features)
    y_train = train.features["is_reference"].to_numpy(dtype=np.int8)
    y_test = test.features["is_reference"].to_numpy(dtype=np.int8)

    _, folds = make_group_folds(train.features, config["n_splits"], config["seed"])
    cv_rows, fold_selectors = _cv_fold_rows(train.features, y_train, folds, config, logger)
    cv_frame = pd.DataFrame(cv_rows)
    cv_frame.to_csv(RESULTS_DIR / "cv_fold_results.csv", index=False)

    cv_summary = (
        cv_frame.groupby("model")
        .agg(
            cv_macro_f1_mean=("candidate_macro_f1", "mean"),
            cv_macro_f1_std=("candidate_macro_f1", "std"),
            cv_f1_mean=("candidate_f1", "mean"),
            cv_accuracy_mean=("candidate_accuracy", "mean"),
            cv_precision_mean=("candidate_precision", "mean"),
            cv_recall_mean=("candidate_recall", "mean"),
            cv_log_loss_mean=("log_loss", "mean"),
            cv_train_seconds_mean=("train_seconds", "mean"),
            cv_inference_seconds_mean=("inference_seconds", "mean"),
        )
        .reset_index()
    )

    ablation_frame = _initial_feature_ablation(train.features, y_train, folds, config, logger)
    ablation_frame.to_csv(RESULTS_DIR / "feature_ablation_fold_results.csv", index=False)
    ablation_summary = (
        ablation_frame.groupby(["model", "feature_set"])
        .agg(candidate_macro_f1=("candidate_macro_f1", "mean"), log_loss=("log_loss", "mean"))
        .reset_index()
    )
    ablation_summary.to_csv(RESULTS_DIR / "feature_ablation_summary.csv", index=False)

    selector = FeatureSelector(
        max_features=config["max_features"],
        correlation_threshold=config["correlation_threshold"],
        permutation_sample_size=config["permutation_sample_size"],
        random_state=config["seed"],
    )
    final_x_train = selector.fit_transform(x_train, y_train)
    final_x_test = selector.transform(x_test)
    selector_report = selector.report()
    selector_report["initial_feature_count"] = len(FEATURE_COLUMNS)
    selector_report["selected_feature_count"] = len(selector.selected_features_)
    (RESULTS_DIR / "feature_selection.json").write_text(json.dumps(selector_report, indent=2))
    pd.DataFrame({"feature": FEATURE_COLUMNS}).to_csv(RESULTS_DIR / "initial_feature_schema.csv", index=False)
    pd.DataFrame({"feature": selector.selected_features_}).to_csv(RESULTS_DIR / "selected_feature_schema.csv", index=False)
    logger(f"final selected features: {selector.selected_features_}")

    student_rows: list[dict[str, Any]] = []
    fitted_estimators: dict[str, Any] = {}
    prediction_frames: list[pd.DataFrame] = []

    for model_name in config["model_names"]:
        model = build_model(model_name, config["seed"], use_selection=False)
        start = time.perf_counter()
        model.fit(final_x_train, y_train)
        train_seconds = time.perf_counter() - start
        probabilities, inference_seconds = _predict(model, final_x_test)
        metrics = candidate_metrics(y_test, probabilities)
        top1 = observation_top1(test.features, probabilities)
        student_rows.append(
            {
                "model": model_name,
                "train_seconds": train_seconds,
                "inference_seconds": inference_seconds,
                "inference_ms_per_1000_rows": 1000.0 * inference_seconds / max(len(final_x_test), 1) * 1000.0,
                "candidate_miss_rate": test_candidate_miss,
                "test_accuracy": metrics["candidate_accuracy"],
                "test_precision": metrics["candidate_precision"],
                "test_recall": metrics["candidate_recall"],
                "test_f1": metrics["candidate_f1"],
                "test_macro_f1": metrics["candidate_macro_f1"],
                "test_log_loss": metrics["log_loss"],
                "test_observation_top1_accuracy": top1["observation_top1_accuracy"],
                "n_observations": top1["n_observations"],
            }
        )
        fitted_estimators[model_name] = model.estimator
        prediction_frame = model.predict_candidates(test.features)
        prediction_frames.append(prediction_frame)
        logger(f"student {model_name}: top1={top1['observation_top1_accuracy']:.4f} macro_f1={metrics['candidate_macro_f1']:.4f}")

    student_frame = pd.DataFrame(student_rows)
    comparison = cv_summary.merge(student_frame, on="model", how="inner")

    def normalized_inverse(series: pd.Series) -> pd.Series:
        low, high = series.min(), series.max()
        if np.isclose(high, low):
            return pd.Series(np.ones(len(series)), index=series.index)
        return (high - series) / (high - low)

    comparison["selection_score"] = (
        0.45 * comparison["cv_macro_f1_mean"]
        + 0.35 * comparison["test_observation_top1_accuracy"]
        + 0.15 * normalized_inverse(comparison["test_log_loss"])
        + 0.05 * normalized_inverse(comparison["inference_ms_per_1000_rows"])
    )
    comparison = comparison.sort_values("selection_score", ascending=False).reset_index(drop=True)
    comparison.to_csv(RESULTS_DIR / "model_comparison.csv", index=False)
    pd.concat(prediction_frames, ignore_index=True).to_csv(RESULTS_DIR / "student_candidate_probabilities.csv", index=False)

    best_name = comparison.loc[0, "model"]
    best = CandidateClassifier(fitted_estimators[best_name], selector=selector, name=best_name)
    best.feature_columns_ = list(FEATURE_COLUMNS)
    artifact_path = best.save(ARTIFACT_DIR / "best_model.joblib")
    metadata = {
        "selected_model": best_name,
        "selection_score": float(comparison.loc[0, "selection_score"]),
        "feature_columns": list(FEATURE_COLUMNS),
        "selected_features": selector.selected_features_,
        "positive_label": 1,
        "binary_target": "candidate arc equals aligned reference arc",
        "random_seed": config["seed"],
        "config": config,
        "overall_train_candidate_miss_rate": float(overall_candidate_miss),
        "test_candidate_miss_rate": float(test_candidate_miss),
        "cv_macro_f1": float(comparison.loc[0, "cv_macro_f1_mean"]),
        "test_observation_top1": float(comparison.loc[0, "test_observation_top1_accuracy"]),
        "test_macro_f1": float(comparison.loc[0, "test_macro_f1"]),
        "test_log_loss": float(comparison.loc[0, "test_log_loss"]),
    }
    (ARTIFACT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))

    reloaded = CandidateClassifier.load(artifact_path)
    reload_probabilities = reloaded.predict_proba(_clean_features(test.features).head(100))
    reload_check = {
        "reloaded_model": reloaded.name,
        "prediction_shape": list(reload_probabilities.shape),
        "probability_min": float(reload_probabilities.min()),
        "probability_max": float(reload_probabilities.max()),
        "all_in_unit_interval": bool(((reload_probabilities >= 0) & (reload_probabilities <= 1)).all()),
    }
    (RESULTS_DIR / "reload_verification.json").write_text(json.dumps(reload_check, indent=2))
    logger(f"reload verification: {reload_check}")

    _plot_comparison(comparison, "cv_macro_f1_mean", "Grouped CV Macro F1", "cv_macro_f1_comparison.png", "Macro F1")
    _plot_comparison(comparison, "test_observation_top1_accuracy", "Student-Test Observation Top-1", "student_top1_comparison.png", "Top-1 accuracy")
    _plot_comparison(comparison, "test_macro_f1", "Student-Test Candidate Macro F1", "student_macro_f1_comparison.png", "Macro F1")
    _plot_comparison(comparison, "test_log_loss", "Student-Test Log Loss", "student_log_loss_comparison.png", "Log loss")
    timing = pd.DataFrame(
        {
            "model": comparison["model"],
            "training_time_s": comparison["cv_train_seconds_mean"],
            "inference_time_s": comparison["inference_seconds"],
        }
    ).melt(id_vars="model", var_name="metric", value_name="seconds")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    colors = {"training_time_s": "#1d4ed8", "inference_time_s": "#f97316"}
    for metric, group in timing.groupby("metric"):
        ax.bar(group["model"], group["seconds"], label=metric, color=colors[metric])
    ax.set_title("Training and Inference Time")
    ax.set_ylabel("seconds")
    ax.tick_params(axis="x", rotation=20)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "timing_comparison.png", dpi=150)
    plt.close(fig)

    summary = {
        "status": "completed",
        "selected_model": best_name,
        "n_train_trips": int(train.features["trip_id"].nunique()),
        "n_test_trips": int(test.features["trip_id"].nunique()),
        "n_train_rows": int(len(train.features)),
        "n_test_rows": int(len(test.features)),
        "overall_train_candidate_miss_rate": float(overall_candidate_miss),
        "test_candidate_miss_rate": float(test_candidate_miss),
        "selected_features": selector.selected_features_,
        "comparison": comparison.to_dict(orient="records"),
        "reload_check": reload_check,
    }
    (RESULTS_DIR / "phase1_summary.json").write_text(json.dumps(summary, indent=2))
    (RESULTS_DIR / "run_log.txt").write_text("\n".join(log_lines) + "\n")
    logger(f"phase 1 complete; selected model: {best_name}")


if __name__ == "__main__":
    run()
