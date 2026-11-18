import csv
import json
import logging
import math
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from api.prediction_service import (
    PredictionServiceError,
    predict_trip,
)

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STUDENT_TEST_DIR = PROJECT_ROOT / "data" / "student_test"
MODEL_COMPARISON_PATH = PROJECT_ROOT / "experiments" / "results" / "model_comparison.csv"
MODEL_METADATA_PATH = PROJECT_ROOT / "artifacts" / "model" / "metadata.json"

app = FastAPI(
    title="PathSnap API",
    description="Map Matching and Route Reconstruction",
    version="1.0.0"
)


cors_origins = [
    origin.strip()
    for origin in os.environ.get("PATHSNAP_FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trip_id: str = Field(pattern=r"^[0-9]{8}$")


def _student_trip_ids() -> list[str]:
    if not STUDENT_TEST_DIR.is_dir():
        raise HTTPException(
            status_code=404,
            detail="Student-test dataset directory not found",
        )
    return sorted(
        entry.name
        for entry in STUDENT_TEST_DIR.iterdir()
        if entry.is_dir() and len(entry.name) == 8 and entry.name.isascii() and entry.name.isdigit()
    )


def _comparison_value(value: str | None):
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


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "running",
        "project": "PathSnap",
        "message": "Backend is working!"
    }


@app.get("/trips")
@app.get("/api/trips")
def list_trips():
    trip_ids = _student_trip_ids()
    return {
        "trips": trip_ids,
        "total": len(trip_ids)
    }


@app.post("/api/predict")
def predict(request: PredictRequest):
    if request.trip_id not in _student_trip_ids():
        raise HTTPException(
            status_code=404,
            detail="Trip ID is not in the student-test partition",
        )

    import time

    start = time.perf_counter()
    try:
        result = predict_trip(request.trip_id)
    except PredictionServiceError as exc:
        if exc.status_code >= 500:
            logger.exception(
                "Prediction service failed for trip %s",
                request.trip_id,
            )
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected prediction failure for trip %s", request.trip_id)
        raise HTTPException(
            status_code=500,
            detail="Prediction pipeline failed due to an internal error",
        ) from exc

    result["processing_time_seconds"] = time.perf_counter() - start
    return result


@app.get("/api/models/comparison")
def models_comparison():
    if not MODEL_COMPARISON_PATH.is_file():
        return {
            "status": "unavailable",
            "message": "Model comparison results are not available",
            "models": [],
        }

    try:
        with MODEL_COMPARISON_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as comparison_file:
            rows = list(csv.DictReader(comparison_file))
    except (OSError, csv.Error, UnicodeError):
        logger.exception("Unable to read model comparison results")
        return {
            "status": "unavailable",
            "message": "Model comparison results could not be read",
            "models": [],
        }

    if not rows or "model" not in rows[0]:
        return {
            "status": "unavailable",
            "message": "Model comparison results contain no model records",
            "models": [],
        }

    metric_names = (
        "cv_macro_f1_mean",
        "cv_macro_f1_std",
        "cv_log_loss_mean",
        "test_macro_f1",
        "test_observation_top1_accuracy",
        "test_log_loss",
        "inference_ms_per_1000_rows",
        "selection_score",
    )
    models = [
        {
            "model_name": row["model"],
            **{
                metric: _comparison_value(row.get(metric))
                for metric in metric_names
                if metric in row
            },
        }
        for row in rows
    ]

    selected_model = None
    if MODEL_METADATA_PATH.is_file():
        try:
            metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
            selected_model = metadata.get("selected_model")
        except (OSError, json.JSONDecodeError):
            logger.exception("Unable to read selected model metadata")

    return {
        "status": "available",
        "selected_model": selected_model,
        "models": models,
    }
