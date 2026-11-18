import json
import math
import operator
import time
from pathlib import Path
from typing import Any

from src.data.dataset_loader import (
    DatasetLoaderError,
    EmptyDatasetFileError,
    MissingDatasetFileError,
    load_trip_data,
)
from src.decoder.hmm_pipeline import decode_candidate_sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "model" / "best_model.joblib"
CONFIG_PATH = PROJECT_ROOT / "experiments" / "configs" / "phase1_config.json"


class PredictionServiceError(RuntimeError):
    status_code = 500


class InvalidPredictionInputError(PredictionServiceError):
    status_code = 422


class PredictionDataNotFoundError(PredictionServiceError):
    status_code = 404


class ModelUnavailableError(PredictionServiceError):
    status_code = 503


class NoCandidatesError(PredictionServiceError):
    status_code = 422


class ImpossiblePredictionError(PredictionServiceError):
    status_code = 422


_MODEL_CACHE: Any | None = None


def _validate_candidate_observation_coverage(
    expected_observation_ids,
    candidate_observation_ids,
) -> None:
    missing_observation_ids = sorted(
        set(expected_observation_ids) - set(candidate_observation_ids)
    )
    if missing_observation_ids:
        sample = missing_observation_ids[:10]
        raise PredictionServiceError(
            f"Candidate generation omitted {len(missing_observation_ids)} "
            f"observations; missing observation IDs (sample): {sample}"
        )


def _load_pipeline_config() -> dict[str, Any]:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelUnavailableError(
            "Prediction configuration is unavailable"
        ) from exc

    required = ("top_k", "search_radius_m", "cell_size_m", "gap_threshold_s")
    if any(key not in config for key in required):
        raise ModelUnavailableError(
            "Prediction configuration is missing required candidate settings"
        )
    return config


def _load_model():
    global _MODEL_CACHE

    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    if not MODEL_PATH.is_file():
        raise ModelUnavailableError("Trained model artifact is not available")

    try:
        from src.models.models import CandidateClassifier

        model = CandidateClassifier.load(MODEL_PATH)
    except Exception as exc:
        raise ModelUnavailableError(
            "Trained model artifact or its runtime dependencies could not be loaded"
        ) from exc

    if not callable(getattr(model, "predict_proba", None)):
        raise ModelUnavailableError(
            "Trained model artifact does not provide predict_proba"
        )
    _MODEL_CACHE = model
    return model


def _make_candidate_trip_data(loaded_trip, gap_threshold_s: float):
    import numpy as np
    import pandas as pd

    track_values = np.asarray(loaded_trip.track, dtype=np.float64)
    node_values = np.asarray(loaded_trip.nodes, dtype=np.float64)
    arc_values = np.asarray(loaded_trip.arcs, dtype=np.int64)

    if (
        track_values.ndim != 2
        or track_values.shape[1] != 3
        or not len(track_values)
    ):
        raise InvalidPredictionInputError(
            "Trip track must contain three numeric values per observation"
        )

    longitude, latitude, timestamp = track_values.T
    if not (
        ((-180.0 <= longitude) & (longitude <= 180.0)).all()
        and ((-90.0 <= latitude) & (latitude <= 90.0)).all()
    ):
        raise InvalidPredictionInputError(
            "Trip track contains coordinates outside valid longitude/latitude ranges"
        )

    dt_s = np.diff(timestamp, prepend=timestamp[0])
    if (dt_s[1:] <= 0.0).any():
        raise InvalidPredictionInputError(
            "Track timestamp values must be strictly increasing"
        )
    if not math.isfinite(float(gap_threshold_s)) or gap_threshold_s < 0:
        raise ModelUnavailableError("Invalid gap threshold in prediction configuration")

    track = pd.DataFrame(
        {
            "trip_id": loaded_trip.trip_id,
            "observation_id": np.arange(len(track_values), dtype=np.int64),
            "longitude": longitude,
            "latitude": latitude,
            "timestamp_s": timestamp,
            "dt_s": dt_s,
            "gap_flag": (dt_s > gap_threshold_s).astype(np.int8),
        }
    )
    nodes = pd.DataFrame(node_values, columns=["longitude", "latitude"])
    arcs = pd.DataFrame(
        arc_values,
        columns=["from_node_id", "to_node_id"],
    )

    return type(
        "PredictionTripData",
        (),
        {
            "trip_id": loaded_trip.trip_id,
            "track": track,
            "nodes": nodes,
            "arcs": arcs,
        },
    )()


def _candidate_arc_index(candidate_id, arc_count: int) -> int:
    if isinstance(candidate_id, bool):
        raise InvalidPredictionInputError("Candidate arc IDs must be integer indices")
    try:
        arc_index = operator.index(candidate_id)
    except TypeError as exc:
        raise InvalidPredictionInputError(
            "Candidate arc IDs must be integer indices"
        ) from exc
    if arc_index < 0 or arc_index >= arc_count:
        raise InvalidPredictionInputError(
            f"Candidate arc ID {arc_index} is outside the trip's arc table"
        )
    return arc_index


def predict_trip(trip_id: str) -> dict[str, Any]:
    import numpy as np
    import pandas as pd

    from src.candidates.candidate_generator import generate_candidates
    from src.features.feature_extractor import FEATURE_COLUMNS, extract_features

    config = _load_pipeline_config()
    try:
        loaded_trip = load_trip_data(trip_id)
    except MissingDatasetFileError as exc:
        raise PredictionDataNotFoundError(
            f"Required input file is missing for trip {trip_id}"
        ) from exc
    except (EmptyDatasetFileError, DatasetLoaderError) as exc:
        raise InvalidPredictionInputError(
            f"Student-test input data for trip {trip_id} is invalid"
        ) from exc

    trip = _make_candidate_trip_data(
        loaded_trip,
        float(config["gap_threshold_s"]),
    )
    model = _load_model()

    try:
        candidate_set = generate_candidates(
            trip,
            top_k=int(config["top_k"]),
            search_radius_m=float(config["search_radius_m"]),
            cell_size_m=float(config["cell_size_m"]),
        )
    except Exception as exc:
        if isinstance(exc, ValueError) and "No objects to concatenate" in str(exc):
            raise NoCandidatesError(
                "No road candidates were generated for this trip"
            ) from exc
        raise PredictionServiceError("Candidate generation failed") from exc

    candidates = getattr(candidate_set, "candidates", None)
    required_candidate_columns = {
        "observation_id",
        "candidate_arc_id",
        "candidate_rank",
    }
    if not isinstance(candidates, pd.DataFrame) or not required_candidate_columns.issubset(
        candidates.columns
    ):
        raise PredictionServiceError(
            "Candidate generator returned an invalid candidate table"
        )
    if candidates.empty:
        raise NoCandidatesError("No road candidates were generated for this trip")

    candidates = candidates.sort_values(
        ["observation_id", "candidate_rank"],
        kind="stable",
    ).reset_index(drop=True)
    try:
        observation_values = pd.to_numeric(
            candidates["observation_id"],
            errors="raise",
        ).to_numpy(dtype=np.float64)
        if (
            not np.isfinite(observation_values).all()
            or not np.equal(observation_values, np.floor(observation_values)).all()
        ):
            raise ValueError("observation IDs must be finite integers")
        candidates["observation_id"] = observation_values.astype(np.int64)
        candidates["candidate_arc_id"] = candidates["candidate_arc_id"].map(
            lambda value: _candidate_arc_index(value, len(loaded_trip.arcs))
        )
    except (TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, InvalidPredictionInputError):
            raise
        raise PredictionServiceError(
            "Candidate generator returned invalid observation or arc IDs"
        ) from exc

    valid_observation_ids = set(range(len(loaded_trip.track)))
    if not set(candidates["observation_id"]).issubset(valid_observation_ids):
        raise PredictionServiceError(
            "Candidate generator returned an unknown observation ID"
        )
    expected_observation_ids = trip.track["observation_id"].tolist()
    _validate_candidate_observation_coverage(
        expected_observation_ids,
        candidates["observation_id"],
    )

    try:
        features = extract_features(trip, candidates)
    except Exception as exc:
        raise PredictionServiceError("Feature extraction failed") from exc
    if not isinstance(features, pd.DataFrame) or features.empty:
        raise NoCandidatesError("Feature extraction produced no candidate rows")
    if len(features) != len(candidates):
        raise PredictionServiceError(
            "Feature extraction changed candidate row count"
        )
    for column in ("observation_id", "candidate_arc_id"):
        if column not in features or not np.array_equal(
            features[column].to_numpy(),
            candidates[column].to_numpy(),
        ):
            raise PredictionServiceError(
                "Feature extraction changed candidate ordering or IDs"
            )

    missing_features = [name for name in FEATURE_COLUMNS if name not in features]
    if missing_features:
        raise PredictionServiceError(
            f"Feature extraction omitted required model features: {missing_features}"
        )
    model_features = (
        features.loc[:, FEATURE_COLUMNS]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )
    try:
        emission_probabilities = np.asarray(
            model.predict_proba(model_features),
            dtype=np.float64,
        )
    except Exception as exc:
        raise PredictionServiceError("Classifier inference failed") from exc
    if (
        emission_probabilities.ndim != 1
        or len(emission_probabilities) != len(candidates)
        or not np.isfinite(emission_probabilities).all()
        or (emission_probabilities < 0.0).any()
        or (emission_probabilities > 1.0).any()
    ):
        raise PredictionServiceError(
            "Classifier returned invalid candidate probabilities"
        )

    candidate_groups = []
    probability_groups = []
    observation_ids = []
    for observation_id, group in candidates.groupby(
        "observation_id",
        sort=False,
    ):
        row_indices = group.index.to_numpy(dtype=np.int64)
        observation_ids.append(int(observation_id))
        candidate_groups.append(group["candidate_arc_id"].tolist())
        probability_groups.append(emission_probabilities[row_indices].tolist())

    track_index = trip.track.set_index("observation_id")
    observation_coordinates = [
        (
            float(track_index.loc[observation_id, "latitude"]),
            float(track_index.loc[observation_id, "longitude"]),
        )
        for observation_id in observation_ids
    ]

    # generate_candidates enumerates rows of trip.arcs and returns those row
    # positions as candidate_arc_id; this mapping follows that source contract.
    arc_endpoint_mapping = {
        arc_id: (int(arc[0]), int(arc[1]))
        for arc_id, arc in enumerate(loaded_trip.arcs)
    }
    node_coordinates = [
        (float(node[1]), float(node[0]))
        for node in loaded_trip.nodes
    ]

    try:
        decoded = decode_candidate_sequence(
            candidate_groups,
            probability_groups,
            observation_coordinates,
            arc_endpoint_mapping,
            node_coordinates,
        )
    except ValueError as exc:
        if "No possible path" in str(exc):
            raise ImpossiblePredictionError(
                "No possible candidate sequence could be decoded"
            ) from exc
        raise InvalidPredictionInputError(
            f"Prediction sequence could not be decoded: {exc}"
        ) from exc

    selected_arc_ids = [
        _candidate_arc_index(candidate_id, len(loaded_trip.arcs))
        for candidate_id in decoded["selected_candidate_ids"]
    ]
    if len(selected_arc_ids) != len(observation_ids):
        raise PredictionServiceError(
            "Decoder returned a sequence with an unexpected length"
        )

    route_segments = []
    selected_probabilities = []
    raw_nodes = loaded_trip.nodes
    raw_arcs = loaded_trip.arcs
    for observation_id, selected_index, arc_id, probs in zip(
        observation_ids,
        decoded["selected_candidate_indices"],
        selected_arc_ids,
        probability_groups,
    ):
        from_node, to_node = raw_arcs[arc_id]
        start_node = raw_nodes[int(from_node)]
        end_node = raw_nodes[int(to_node)]
        route_segments.append(
            {
                "observation_id": observation_id,
                "candidate_arc_id": arc_id,
                "coordinates": [
                    [float(start_node[0]), float(start_node[1])],
                    [float(end_node[0]), float(end_node[1])],
                ],
            }
        )
        selected_probabilities.append(float(probs[selected_index]))

    return {
        "trip_id": trip_id,
        "status": "completed",
        "selected_candidate_ids": selected_arc_ids,
        "selected_candidate_indices": decoded["selected_candidate_indices"],
        "predicted_road_sequence": [
            {
                "observation_id": observation_id,
                "road_arc_id": arc_id,
            }
            for observation_id, arc_id in zip(observation_ids, selected_arc_ids)
        ],
        "route_geometry": {
            "type": "MultiLineString",
            "coordinates": [segment["coordinates"] for segment in route_segments],
        },
        "route_segments": route_segments,
        "observation_ids": observation_ids,
        "selected_candidate_probabilities": selected_probabilities,
        "final_best_log_probability": decoded["final_best_log_probability"],
        "number_of_observations": decoded["number_of_observations"],
        "decoder_name": decoded["decoder_name"],
        "model_name": getattr(model, "name", "unknown"),
        "candidate_generation_stats": getattr(candidate_set, "stats", {}),
    }
