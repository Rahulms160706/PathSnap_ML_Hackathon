import math
import re
from dataclasses import dataclass
from pathlib import Path


TRIP_ID_PATTERN = re.compile(r"^\d{8}$")


class DatasetLoaderError(ValueError):
    """Base exception for dataset loading failures."""


class InvalidTripIdError(DatasetLoaderError):
    """Raised when a trip ID is not an eight-digit string."""


class MissingDatasetFileError(DatasetLoaderError):
    """Raised when a required prediction-input file is missing."""


class EmptyDatasetFileError(DatasetLoaderError):
    """Raised when a required prediction-input file is empty."""


class MalformedDatasetFileError(DatasetLoaderError):
    """Raised when a required prediction-input file is malformed."""


@dataclass(frozen=True)
class TripData:
    trip_id: str
    track: tuple[tuple[float, float, float], ...]
    nodes: tuple[tuple[float, float], ...]
    arcs: tuple[tuple[int, int], ...]


def validate_trip_id(trip_id: str) -> str:
    if not isinstance(trip_id, str) or TRIP_ID_PATTERN.fullmatch(trip_id) is None:
        raise InvalidTripIdError(
            "Trip ID must be a string containing exactly eight digits"
        )
    return trip_id


def _read_numeric_rows(
    file_path: Path,
    column_count: int,
    numeric_type: type,
) -> list[tuple]:
    if not file_path.is_file():
        raise MissingDatasetFileError(
            f"Required dataset file is missing: {file_path}"
        )

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise MalformedDatasetFileError(
            f"Could not read dataset file: {file_path}"
        ) from exc

    non_empty_lines = [line for line in lines if line.strip()]
    if not non_empty_lines:
        raise EmptyDatasetFileError(
            f"Dataset file is empty: {file_path}"
        )

    rows = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        fields = line.split()
        if len(fields) != column_count:
            raise MalformedDatasetFileError(
                f"{file_path.name} has {len(fields)} columns on line "
                f"{line_number}; expected {column_count}"
            )

        try:
            parsed = tuple(numeric_type(field) for field in fields)
        except (TypeError, ValueError, OverflowError) as exc:
            raise MalformedDatasetFileError(
                f"{file_path.name} contains a non-numeric value on line "
                f"{line_number}"
            ) from exc

        if any(isinstance(value, float) and not math.isfinite(value) for value in parsed):
            raise MalformedDatasetFileError(
                f"{file_path.name} contains a non-finite value on line "
                f"{line_number}"
            )

        if numeric_type is int:
            try:
                original_fields = tuple(field for field in fields)
                if any(
                    not re.fullmatch(r"[+-]?\d+", original_field)
                    for original_field in original_fields
                ):
                    raise ValueError
            except ValueError as exc:
                raise MalformedDatasetFileError(
                    f"{file_path.name} contains a non-integer value on line "
                    f"{line_number}"
                ) from exc

        rows.append(parsed)

    return rows


def load_trip_data(
    trip_id: str,
    data_root: Path | str | None = None,
) -> TripData:
    trip_id = validate_trip_id(trip_id)

    if data_root is None:
        project_root = Path(__file__).resolve().parents[2]
        student_test_dir = project_root / "data" / "student_test"
    else:
        student_test_dir = Path(data_root) / "student_test"

    trip_dir = student_test_dir / trip_id

    track_rows = _read_numeric_rows(
        trip_dir / f"{trip_id}.track",
        column_count=3,
        numeric_type=float,
    )
    node_rows = _read_numeric_rows(
        trip_dir / f"{trip_id}.nodes",
        column_count=2,
        numeric_type=float,
    )
    arc_rows = _read_numeric_rows(
        trip_dir / f"{trip_id}.arcs",
        column_count=2,
        numeric_type=int,
    )

    return TripData(
        trip_id=trip_id,
        track=tuple(track_rows),
        nodes=tuple(node_rows),
        arcs=tuple(arc_rows),
    )
