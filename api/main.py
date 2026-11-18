from __future__ import annotations

import csv
import json
import logging
import math
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.candidates.candidate_generator import generate_candidates
from src.data.preprocessing import align_reference_route, load_trip
from src.decoder.hmm_pipeline import decode_candidate_sequence
from src.evaluation.evaluate import candidate_metrics
from src.features.feature_extractor import extract_features
from src.models.models import CandidateClassifier

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "evaluator_test"
CONFIG_PATH = ROOT / "experiments" / "configs" / "phase1_config.json"
ARTIFACT_DIR = ROOT / "artifacts" / "model"
MODEL_PATH = ARTIFACT_DIR / "best_model.joblib"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"
RESULTS_DIR = ROOT / "experiments" / "results"
MODEL_COMPARISON_PATH = RESULTS_DIR / "model_comparison.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("pathsnap.api")

app = FastAPI(
    title="PathSnap API",
    description="Map matching and route reconstruction",
    version="1.0.0",
)

_cors_origins = (
    os.getenv("PATHSNAP_CORS_ORIGINS")
    or os.getenv("PATHSNAP_FRONTEND_ORIGINS")
    or "*"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text())


@lru_cache(maxsize=1)
def get_metadata() -> dict[str, Any]:
    return json.loads(METADATA_PATH.read_text())


@lru_cache(maxsize=1)
def get_model() -> CandidateClassifier:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model artifact not found: {MODEL_PATH}")
    return CandidateClassifier.load(MODEL_PATH)


def list_trip_ids() -> list[str]:
    if not DATA_DIR.is_dir():
        raise FileNotFoundError(f"Evaluator-test directory not found: {DATA_DIR}")
    trip_ids = sorted(
        entry.name
        for entry in DATA_DIR.iterdir()
        if entry.is_dir() and len(entry.name) == 8 and entry.name.isdigit()
    )
    if not trip_ids:
        raise FileNotFoundError("No valid trip folders found in the evaluator-test dataset")
    return trip_ids


def error_response(status_code: int, trip_id: str | None, message: str) -> JSONResponse:
    payload: dict[str, Any] = {"status": "error", "message": message}
    if trip_id is not None:
        payload["trip_id"] = trip_id
    return JSONResponse(status_code=status_code, content=payload)


def safe_float(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        return 0.0
    return number


def build_route_coordinates(
    trip: Any,
    arc_ids: list[int],
) -> list[list[float]]:
    node_longitude = trip.nodes["longitude"].to_numpy(dtype=np.float64)
    node_latitude = trip.nodes["latitude"].to_numpy(dtype=np.float64)
    from_node = trip.arcs["from_node_id"].to_numpy(dtype=np.int64)
    to_node = trip.arcs["to_node_id"].to_numpy(dtype=np.int64)

    coordinates: list[list[float]] = []
    previous_end_node: int | None = None

    for arc_id in arc_ids:
        start_node = int(from_node[arc_id])
        end_node = int(to_node[arc_id])
        if previous_end_node == end_node:
            start_node, end_node = end_node, start_node

        start = [safe_float(node_longitude[start_node]), safe_float(node_latitude[start_node])]
        end = [safe_float(node_longitude[end_node]), safe_float(node_latitude[end_node])]
        if not coordinates or coordinates[-1] != start:
            coordinates.append(start)
        coordinates.append(end)
        previous_end_node = end_node

    return coordinates


def build_route_points(
    trip: Any,
    arc_ids: list[int],
) -> list[dict[str, Any]]:
    node_longitude = trip.nodes["longitude"].to_numpy(dtype=np.float64)
    node_latitude = trip.nodes["latitude"].to_numpy(dtype=np.float64)
    from_node = trip.arcs["from_node_id"].to_numpy(dtype=np.int64)
    to_node = trip.arcs["to_node_id"].to_numpy(dtype=np.int64)

    points: list[dict[str, Any]] = []
    previous_end_node: int | None = None

    for segment_index, arc_id in enumerate(arc_ids):
        start_node = int(from_node[arc_id])
        end_node = int(to_node[arc_id])
        if previous_end_node == end_node:
            start_node, end_node = end_node, start_node

        start = {
            "lat": safe_float(node_latitude[start_node]),
            "lon": safe_float(node_longitude[start_node]),
            "arc_id": int(arc_id),
            "segment_index": segment_index,
        }
        end = {
            "lat": safe_float(node_latitude[end_node]),
            "lon": safe_float(node_longitude[end_node]),
            "arc_id": int(arc_id),
            "segment_index": segment_index,
        }
        if not points or (
            points[-1]["lat"] != start["lat"] or points[-1]["lon"] != start["lon"]
        ):
            points.append(start)
        points.append(end)
        previous_end_node = end_node

    return points


def build_road_network(trip: Any, arc_ids: list[int]) -> list[dict[str, Any]]:
    node_longitude = trip.nodes["longitude"].to_numpy(dtype=np.float64)
    node_latitude = trip.nodes["latitude"].to_numpy(dtype=np.float64)
    from_node = trip.arcs["from_node_id"].to_numpy(dtype=np.int64)
    to_node = trip.arcs["to_node_id"].to_numpy(dtype=np.int64)

    network: list[dict[str, Any]] = []
    for arc_id in dict.fromkeys(int(value) for value in arc_ids):
        start_node = int(from_node[arc_id])
        end_node = int(to_node[arc_id])
        network.append(
            {
                "arc_id": arc_id,
                "from_node": start_node,
                "to_node": end_node,
                "coordinates": [
                    [safe_float(node_latitude[start_node]), safe_float(node_longitude[start_node])],
                    [safe_float(node_latitude[end_node]), safe_float(node_longitude[end_node])],
                ],
            }
        )
    return network


def route_continuity(trip: Any, arc_ids: list[int]) -> float:
    if len(arc_ids) < 2:
        return 0.0
    from_node = trip.arcs["from_node_id"].to_numpy(dtype=np.int64)
    to_node = trip.arcs["to_node_id"].to_numpy(dtype=np.int64)
    connected = 0
    for previous, current in zip(arc_ids[:-1], arc_ids[1:]):
        if (
            to_node[previous] == from_node[current]
            or from_node[previous] == to_node[current]
        ):
            connected += 1
    return connected / (len(arc_ids) - 1)


def comparison_value(value: str | None) -> Any:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    if not math.isfinite(number):
        return None
    if number.is_integer():
        return int(number)
    return number


def normalize_model_name(name: str | None) -> str | None:
    if not name:
        return None
    suffix = "_bayesian_tuned"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return name


def model_family(name: str) -> str:
    normalized = normalize_model_name(name) or ""
    if "knn" in normalized:
        return "Instance-Based"
    if "logistic" in normalized:
        return "Linear"
    if "forest" in normalized:
        return "Ensemble"
    if "extra" in normalized:
        return "Tree-Based"
    if "gradient" in normalized or "boost" in normalized:
        return "Boosting"
    return "Other"


def run_prediction(
    trip_id: str,
    include_metrics: bool = True,
    include_road_network: bool = True,
) -> JSONResponse:
    started = time.perf_counter()
    logger.info("Received prediction request: trip_id=%s", trip_id)

    if len(trip_id) != 8 or not trip_id.isdigit():
        return error_response(404, trip_id, "Invalid trip ID: expected exactly eight digits")

    trip_dir = DATA_DIR / trip_id
    if not trip_dir.is_dir():
        return error_response(404, trip_id, f"Trip not found: {trip_id}")

    try:
        config = get_config()
        metadata = get_metadata()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.exception("Failed to load configuration or metadata")
        return error_response(500, trip_id, f"Server configuration error: {exc}")

    try:
        model = get_model()
    except (OSError, ValueError, FileNotFoundError) as exc:
        logger.exception("Failed to load model artifact")
        return error_response(503, trip_id, f"Model artifact unavailable: {exc}")

    try:
        logger.info("Loading trip %s", trip_id)
        trip = load_trip(trip_dir, float(config["gap_threshold_s"]))

        logger.info("Generating candidates for trip %s", trip_id)
        candidate_set = generate_candidates(
            trip,
            top_k=int(config["top_k"]),
            search_radius_m=float(config["search_radius_m"]),
            cell_size_m=float(config["cell_size_m"]),
        )
        if candidate_set.candidates.empty:
            return error_response(
                422,
                trip_id,
                "No road candidates found for one or more observations",
            )

        logger.info("Extracting features for trip %s", trip_id)
        labels = align_reference_route(trip)
        features = extract_features(trip, candidate_set.candidates, labels)
        if features.empty:
            return error_response(422, trip_id, "No features generated for this trip")

        features = features.sort_values(["observation_id", "candidate_rank"]).reset_index(drop=True)

        logger.info("Running %s for trip %s", model.name, trip_id)
        model_started = time.perf_counter()
        probabilities = model.predict_proba(features)
        model_latency_ms = (time.perf_counter() - model_started) * 1000.0
        if len(probabilities) != len(features):
            return error_response(500, trip_id, "Model returned an invalid number of predictions")

        emission_probabilities = np.clip(probabilities.astype(np.float64), 1e-9, 1.0 - 1e-9)
        candidate_groups: list[list[int]] = []
        emission_groups: list[list[float]] = []
        observation_ids: list[int] = []
        for observation_id, group in features.groupby("observation_id", sort=True):
            candidate_groups.append([int(value) for value in group["candidate_arc_id"]])
            emission_groups.append([float(value) for value in emission_probabilities[group.index]])
            observation_ids.append(int(observation_id))

        if not candidate_groups or any(not group for group in candidate_groups):
            return error_response(422, trip_id, "No candidate sequence available for decoding")

        track_index = trip.track.set_index("observation_id")
        observation_coordinates = [
            (
                float(track_index.at[observation_id, "latitude"]),
                float(track_index.at[observation_id, "longitude"]),
            )
            for observation_id in observation_ids
        ]
        node_coordinates = [
            (float(latitude), float(longitude))
            for longitude, latitude in zip(
                trip.nodes["longitude"].to_numpy(),
                trip.nodes["latitude"].to_numpy(),
            )
        ]
        arc_endpoint_mapping = {
            int(arc_id): (int(from_node), int(to_node))
            for arc_id, from_node, to_node in zip(
                trip.arcs.index,
                trip.arcs["from_node_id"],
                trip.arcs["to_node_id"],
            )
        }

        logger.info("Running Viterbi decoder for trip %s", trip_id)
        decoder_started = time.perf_counter()
        try:
            decoded = decode_candidate_sequence(
                candidate_groups=candidate_groups,
                emission_probability_groups=emission_groups,
                observation_coordinates=observation_coordinates,
                arc_endpoint_mapping=arc_endpoint_mapping,
                node_coordinates=node_coordinates,
            )
        except ValueError as exc:
            return error_response(422, trip_id, f"Viterbi decoding failed: {exc}")
        decoder_latency_ms = (time.perf_counter() - decoder_started) * 1000.0

        selected_arcs = [int(value) for value in decoded["selected_candidate_ids"]]
        selected_indices = [int(value) for value in decoded["selected_candidate_indices"]]
        collapsed_arcs: list[int] = []
        for arc_id in selected_arcs:
            if not collapsed_arcs or arc_id != collapsed_arcs[-1]:
                collapsed_arcs.append(arc_id)
        if not collapsed_arcs:
            return error_response(422, trip_id, "Empty predicted route")

        logger.info("Evaluating prediction for trip %s", trip_id)
        labels_by_observation = features.groupby("observation_id")["reference_arc_id"].first()
        decoded_hits = 0
        for observation_id, arc_id in zip(observation_ids, selected_arcs):
            if int(labels_by_observation.at[observation_id]) == arc_id:
                decoded_hits += 1
        decoded_accuracy = decoded_hits / len(selected_arcs)

        truth_route_arcs = {int(value) for value in trip.route}
        predicted_route_arcs = set(collapsed_arcs)
        true_positive = len(truth_route_arcs & predicted_route_arcs)
        route_precision = true_positive / len(predicted_route_arcs) if predicted_route_arcs else 0.0
        route_recall = true_positive / len(truth_route_arcs) if truth_route_arcs else 0.0
        route_f1 = (
            2.0 * route_precision * route_recall / (route_precision + route_recall)
            if route_precision + route_recall > 0.0
            else 0.0
        )
        classifier_metrics = candidate_metrics(
            features["is_reference"].to_numpy(dtype=np.int8),
            probabilities,
        )
        continuity = route_continuity(trip, collapsed_arcs)
        predicted_coordinates = build_route_coordinates(trip, collapsed_arcs)
        predicted_route_points = build_route_points(trip, collapsed_arcs)
        road_network = build_road_network(trip, collapsed_arcs) if include_road_network else []
        gps_trajectory = [
            {
                "lat": safe_float(row.latitude),
                "lon": safe_float(row.longitude),
                "timestamp": safe_float(row.timestamp_s),
            }
            for row in trip.track.itertuples()
        ]
        model_info = {
            "classifier": model.name,
            "decoder": "HMM + Viterbi",
            "hyperparameters": metadata.get("best_params", {}),
            "candidate_radius_m": safe_float(config.get("search_radius_m", 0.0)),
            "features_used": metadata.get("selected_features", []),
        }

        node_longitude = trip.nodes["longitude"].to_numpy(dtype=np.float64)
        node_latitude = trip.nodes["latitude"].to_numpy(dtype=np.float64)
        from_node = trip.arcs["from_node_id"].to_numpy(dtype=np.int64)
        to_node = trip.arcs["to_node_id"].to_numpy(dtype=np.int64)
        route_segments = []
        for observation_id, arc_id in zip(observation_ids, selected_arcs):
            start_node = int(from_node[arc_id])
            end_node = int(to_node[arc_id])
            route_segments.append(
                {
                    "observation_id": observation_id,
                    "candidate_arc_id": arc_id,
                    "coordinates": [
                        [safe_float(node_longitude[start_node]), safe_float(node_latitude[start_node])],
                        [safe_float(node_longitude[end_node]), safe_float(node_latitude[end_node])],
                    ],
                }
            )

        selected_probabilities: list[float] = []
        for selected_index, probability_group in zip(selected_indices, emission_groups):
            selected_probabilities.append(safe_float(probability_group[selected_index]))

        gps_observations = [
            {
                "observation_id": int(row.observation_id),
                "longitude": safe_float(row.longitude),
                "latitude": safe_float(row.latitude),
                "timestamp_s": safe_float(row.timestamp_s),
                "coordinates": [safe_float(row.longitude), safe_float(row.latitude)],
            }
            for row in trip.track.itertuples()
        ]

        latency_ms = safe_float((time.perf_counter() - started) * 1000.0)
        metrics_payload = {
            "accuracy": safe_float(decoded_accuracy),
            "precision": safe_float(route_precision),
            "recall": safe_float(route_recall),
            "macro_f1": safe_float(classifier_metrics["candidate_macro_f1"]),
            "log_loss": safe_float(classifier_metrics["log_loss"]),
            "route_continuity": safe_float(continuity),
            "inference_time_ms": latency_ms,
            "classifier_time_ms": safe_float(model_latency_ms),
            "viterbi_time_ms": safe_float(decoder_latency_ms),
            "total_arcs_matched": int(decoded_hits),
            "arcs_correct": int(decoded_hits),
            "f1": safe_float(route_f1),
            "candidate_accuracy": safe_float(classifier_metrics["candidate_accuracy"]),
            "candidate_precision": safe_float(classifier_metrics["candidate_precision"]),
            "candidate_recall": safe_float(classifier_metrics["candidate_recall"]),
            "candidate_f1": safe_float(classifier_metrics["candidate_f1"]),
            "candidate_macro_f1": safe_float(classifier_metrics["candidate_macro_f1"]),
            "decoded_top1_accuracy": safe_float(decoded_accuracy),
        }
        response: dict[str, Any] = {
            "status": "completed",
            "success": True,
            "trip_id": trip_id,
            "gps_trajectory": gps_trajectory,
            "predicted_route": predicted_route_points,
            "predicted_route_array": predicted_coordinates,
            "road_network": road_network,
            "model_info": model_info,
            "inference_time_ms": latency_ms,
            "message": "Route reconstructed successfully",
            "model": {
                "name": model.name,
                "artifact": str(MODEL_PATH.relative_to(ROOT)),
                "bayesian_optimized": bool(metadata.get("bayesian_optimized", False)),
                "best_params": metadata.get("best_params", {}),
            },
            "decoder": {
                "name": "viterbi",
                "implementation": decoded["decoder_name"],
                "final_log_probability": safe_float(decoded["final_best_log_probability"]),
            },
            "model_name": model.name,
            "decoder_name": decoded["decoder_name"],
            "gps_observations": gps_observations,
            "observation_ids": observation_ids,
            "predicted_road_sequence": [
                {"observation_id": observation_id, "road_arc_id": arc_id}
                for observation_id, arc_id in zip(observation_ids, selected_arcs)
            ],
            "selected_candidate_ids": selected_arcs,
            "selected_candidate_indices": selected_indices,
            "selected_candidate_probabilities": selected_probabilities,
            "final_best_log_probability": safe_float(decoded["final_best_log_probability"]),
            "number_of_observations": int(decoded["number_of_observations"]),
            "candidate_generation_stats": {
                key: safe_float(value) if isinstance(value, (int, float, np.number)) else value
                for key, value in candidate_set.stats.items()
            },
            "predicted_arc_ids": collapsed_arcs,
            "route_geometry": {
                "type": "MultiLineString",
                "coordinates": [segment["coordinates"] for segment in route_segments],
            },
            "predicted_route_geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": predicted_coordinates},
                        "properties": {"trip_id": trip_id, "arc_ids": collapsed_arcs},
                    }
                ],
            },
            "route_segments": route_segments,
            "metrics": metrics_payload if include_metrics else None,
            "counts": {
                "gps_observations": len(gps_observations),
                "candidate_rows": len(features),
                "decoded_observations": len(selected_arcs),
                "predicted_route_arcs": len(collapsed_arcs),
            },
            "latency_ms": latency_ms,
            "processing_time_seconds": latency_ms / 1000.0,
            "model_latency_ms": safe_float(model_latency_ms),
            "decoder_latency_ms": safe_float(decoder_latency_ms),
        }
        logger.info("Prediction completed in %.1f ms", latency_ms)
        return JSONResponse(status_code=200, content=response)
    except Exception as exc:
        logger.exception("Prediction failed for trip %s", trip_id)
        return error_response(500, trip_id, f"Prediction failed: {exc}")


@app.get("/api/health")
@app.get("/health")
def health_check() -> dict[str, Any]:
    try:
        trips = list_trip_ids()
    except FileNotFoundError:
        trips = []
    try:
        metadata = get_metadata()
    except (OSError, ValueError, json.JSONDecodeError):
        metadata = {}
    model_available = MODEL_PATH.is_file()
    status = "healthy" if model_available and trips else "degraded" if model_available else "error"
    return {
        "status": status,
        "project": "PathSnap",
        "version": app.version or "1.0.0",
        "message": "Backend is working!",
        "active_model": metadata.get("selected_model"),
        "evaluator_trips_count": len(trips),
        "model_artifact": model_available,
        "n_trips": len(trips),
    }


@app.get("/api/trips")
@app.get("/trips")
def list_trips() -> Any:
    try:
        trip_ids = list_trip_ids()
    except FileNotFoundError as exc:
        return error_response(404, None, str(exc))
    trip_summaries = [
        {"trip_id": trip_id, "partition": "evaluator_test"} for trip_id in trip_ids
    ]
    return {"trips": trip_summaries, "total": len(trip_ids), "count": len(trip_ids)}


@app.post("/api/predict")
@app.post("/predict")
def predict(request: dict[str, Any] = Body(...)) -> JSONResponse:
    trip_id = request.get("trip_id")
    if trip_id is None:
        return error_response(400, None, "Request body must contain 'trip_id'")
    if not isinstance(trip_id, str):
        return error_response(400, str(trip_id), "trip_id must be a string")
    include_metrics = bool(request.get("include_metrics", True))
    include_road_network = bool(request.get("include_road_network", True))
    return run_prediction(trip_id.strip(), include_metrics, include_road_network)


@app.get("/api/models/comparison")
@app.get("/models/comparison")
def models_comparison() -> JSONResponse:
    if not MODEL_COMPARISON_PATH.is_file():
        return JSONResponse(
            status_code=200,
            content={
                "status": "unavailable",
                "message": "Model comparison results are not available",
                "models": [],
            },
        )

    try:
        with MODEL_COMPARISON_PATH.open("r", encoding="utf-8-sig", newline="") as comparison_file:
            rows = list(csv.DictReader(comparison_file))
    except (OSError, csv.Error, UnicodeError):
        logger.exception("Unable to read model comparison results")
        return JSONResponse(
            status_code=200,
            content={
                "status": "unavailable",
                "message": "Model comparison results could not be read",
                "models": [],
            },
        )

    metric_names = (
        "cv_macro_f1_mean",
        "cv_macro_f1_std",
        "cv_log_loss_mean",
        "test_accuracy",
        "test_precision",
        "test_recall",
        "test_macro_f1",
        "test_observation_top1_accuracy",
        "test_log_loss",
        "train_seconds",
        "inference_ms_per_1000_rows",
        "selection_score",
    )
    try:
        selected_model = get_metadata().get("selected_model")
    except (OSError, ValueError, json.JSONDecodeError):
        selected_model = None
    selected_base_model = normalize_model_name(selected_model)

    models: list[dict[str, Any]] = []
    for row in rows:
        model_name = row.get("model")
        if not model_name:
            continue
        metrics = {
            metric: comparison_value(row.get(metric))
            for metric in metric_names
            if metric in row
        }
        is_selected = selected_base_model == model_name
        model_item: dict[str, Any] = {
            "model_name": model_name,
            "model_family": model_family(model_name),
            "accuracy": metrics.get("test_accuracy"),
            "precision": metrics.get("test_precision"),
            "recall": metrics.get("test_recall"),
            "macro_f1": metrics.get("cv_macro_f1_mean"),
            "log_loss": metrics.get("test_log_loss"),
            "training_time_s": metrics.get("train_seconds"),
            "inference_time_ms": metrics.get("inference_ms_per_1000_rows"),
            "is_selected": is_selected,
            **metrics,
        }
        if is_selected:
            model_item["selection_notes"] = "Bayesian-tuned variant promoted as champion"
        models.append(model_item)

    return JSONResponse(
        status_code=200,
        content={
            "status": "available",
            "selected_model": selected_model,
            "selected_model_name": selected_model,
            "selection_criterion": "5-fold grouped CV macro F1 and selection score",
            "comparison_dataset": "candidate rows from the training partition",
            "models": models,
        },
    )


@app.get("/api/evaluation/summary")
@app.get("/evaluation/summary")
def evaluation_summary() -> JSONResponse:
    path = RESULTS_DIR / "phase1_summary.json"
    if not path.is_file():
        return error_response(404, None, "Evaluation summary not found")
    summary = json.loads(path.read_text())
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "selected_model": summary.get("selected_model"),
            "bayesian_optimization": summary.get("bayesian_optimization"),
            "comparison": summary.get("comparison", []),
        },
    )
