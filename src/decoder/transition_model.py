import math
from collections.abc import Mapping, Sequence
from operator import index


EARTH_RADIUS_M = 6_371_008.8


def haversine_distance_m(
    coordinate_a: Sequence[float],
    coordinate_b: Sequence[float],
) -> float:
    """Calculate great-circle distance using latitude/longitude coordinates."""
    lat_a, lon_a = _validate_coordinate(coordinate_a, "coordinate_a")
    lat_b, lon_b = _validate_coordinate(coordinate_b, "coordinate_b")

    lat_a_rad = math.radians(lat_a)
    lat_b_rad = math.radians(lat_b)
    delta_lat = lat_b_rad - lat_a_rad
    delta_lon = math.radians(lon_b - lon_a)

    haversine_value = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat_a_rad)
        * math.cos(lat_b_rad)
        * math.sin(delta_lon / 2.0) ** 2
    )
    haversine_value = min(1.0, max(0.0, haversine_value))
    central_angle = 2.0 * math.asin(math.sqrt(haversine_value))
    return EARTH_RADIUS_M * central_angle


def _validate_coordinate(
    coordinate: Sequence[float],
    name: str,
) -> tuple[float, float]:
    if (
        isinstance(coordinate, (str, bytes))
        or not isinstance(coordinate, Sequence)
        or len(coordinate) != 2
    ):
        raise ValueError(f"{name} must be a two-value latitude/longitude sequence")

    try:
        latitude = float(coordinate[0])
        longitude = float(coordinate[1])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain numeric coordinates") from exc

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError(f"{name} must contain finite coordinates")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"{name} has latitude outside [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"{name} has longitude outside [-180, 180]")
    return latitude, longitude


def _as_sequence(value, name: str) -> list:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a sequence")
    if not isinstance(value, Sequence):
        try:
            return list(value)
        except TypeError as exc:
            raise ValueError(f"{name} must be a sequence") from exc
    return list(value)


def _arc_midpoint(
    endpoint_node_a: int,
    endpoint_node_b: int,
    node_coordinates: Sequence[Sequence[float]],
) -> tuple[float, float]:
    coordinate_a = _validate_coordinate(
        node_coordinates[endpoint_node_a],
        f"node_coordinates[{endpoint_node_a}]",
    )
    coordinate_b = _validate_coordinate(
        node_coordinates[endpoint_node_b],
        f"node_coordinates[{endpoint_node_b}]",
    )
    return (
        (coordinate_a[0] + coordinate_b[0]) / 2.0,
        (coordinate_a[1] + coordinate_b[1]) / 2.0,
    )


def build_transition_probabilities(
    candidate_groups,
    observation_coordinates,
    arc_endpoint_mapping,
    node_coordinates,
    *,
    distance_scale_m=100.0,
    minimum_probability=1e-6,
) -> list[list[list[float]]]:
    """
    Build geometry-based movement-consistency transition matrices.

    coordinate convention is not inferred: callers must explicitly supply
    observation and node coordinates as (latitude, longitude). This model does
    not use road-network connectivity or candidate arc direction.
    """
    candidate_groups = _as_sequence(candidate_groups, "candidate_groups")
    observation_coordinates = _as_sequence(
        observation_coordinates,
        "observation_coordinates",
    )
    node_coordinates = _as_sequence(node_coordinates, "node_coordinates")

    if not candidate_groups:
        raise ValueError("candidate_groups must contain at least one observation")
    if len(candidate_groups) != len(observation_coordinates):
        raise ValueError(
            "candidate_groups and observation_coordinates must have "
            "the same number of observations"
        )
    if not isinstance(arc_endpoint_mapping, Mapping):
        raise ValueError("arc_endpoint_mapping must be a mapping")
    if not isinstance(distance_scale_m, (int, float)) or isinstance(
        distance_scale_m, bool
    ):
        raise ValueError("distance_scale_m must be a positive finite number")
    distance_scale_m = float(distance_scale_m)
    if not math.isfinite(distance_scale_m) or distance_scale_m <= 0.0:
        raise ValueError("distance_scale_m must be a positive finite number")
    if not isinstance(minimum_probability, (int, float)) or isinstance(
        minimum_probability, bool
    ):
        raise ValueError("minimum_probability must be between 0 and 1")
    minimum_probability = float(minimum_probability)
    if (
        not math.isfinite(minimum_probability)
        or minimum_probability <= 0.0
        or minimum_probability > 1.0
    ):
        raise ValueError(
            "minimum_probability must be a positive finite number between 0 and 1"
        )

    validated_observations = [
        _validate_coordinate(coordinate, f"observation_coordinates[{index}]")
        for index, coordinate in enumerate(observation_coordinates)
    ]

    if not node_coordinates:
        raise ValueError("node_coordinates must not be empty")

    validated_groups = []
    arc_midpoints = {}

    for observation_index, candidate_group in enumerate(candidate_groups):
        candidates = _as_sequence(
            candidate_group,
            f"candidate_groups[{observation_index}]",
        )
        if not candidates:
            raise ValueError(
                f"candidate_groups[{observation_index}] must not be empty"
            )

        validated_group = []
        for candidate_index, candidate_arc_id in enumerate(candidates):
            try:
                hash(candidate_arc_id)
            except TypeError as exc:
                raise ValueError(
                    f"candidate arc ID at candidate "
                    f"groups[{observation_index}][{candidate_index}] "
                    "must be hashable"
                ) from exc

            if candidate_arc_id not in arc_endpoint_mapping:
                raise ValueError(
                    f"Missing arc endpoint mapping for candidate_arc_id "
                    f"{candidate_arc_id!r}"
                )
            if candidate_arc_id not in arc_midpoints:
                endpoints = arc_endpoint_mapping[candidate_arc_id]
                if (
                    isinstance(endpoints, (str, bytes))
                    or not isinstance(endpoints, Sequence)
                    or len(endpoints) != 2
                ):
                    raise ValueError(
                        f"Arc endpoint mapping for candidate_arc_id "
                        f"{candidate_arc_id!r} must contain two node indices"
                    )

                try:
                    if isinstance(endpoints[0], bool) or isinstance(endpoints[1], bool):
                        raise TypeError
                    endpoint_a = index(endpoints[0])
                    endpoint_b = index(endpoints[1])
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValueError(
                        f"Arc endpoint mapping for candidate_arc_id "
                        f"{candidate_arc_id!r} must contain integer node indices"
                    ) from exc

                if (
                    endpoint_a < 0
                    or endpoint_a >= len(node_coordinates)
                    or endpoint_b < 0
                    or endpoint_b >= len(node_coordinates)
                ):
                    raise ValueError(
                        f"Arc endpoint mapping for candidate_arc_id "
                        f"{candidate_arc_id!r} contains an invalid node index"
                    )

                arc_midpoints[candidate_arc_id] = _arc_midpoint(
                    endpoint_a,
                    endpoint_b,
                    node_coordinates,
                )

            validated_group.append(candidate_arc_id)

        validated_groups.append(validated_group)

    transition_matrices = []
    for previous_observation_index in range(len(validated_groups) - 1):
        previous_candidates = validated_groups[previous_observation_index]
        current_candidates = validated_groups[previous_observation_index + 1]
        gps_displacement = haversine_distance_m(
            validated_observations[previous_observation_index],
            validated_observations[previous_observation_index + 1],
        )

        matrix = []
        for previous_candidate_id in previous_candidates:
            previous_midpoint = arc_midpoints[previous_candidate_id]
            raw_scores = []

            for current_candidate_id in current_candidates:
                current_midpoint = arc_midpoints[current_candidate_id]
                candidate_displacement = haversine_distance_m(
                    previous_midpoint,
                    current_midpoint,
                )
                difference_m = abs(candidate_displacement - gps_displacement)
                raw_score = math.exp(-difference_m / distance_scale_m)
                raw_scores.append(max(raw_score, minimum_probability))

            score_total = sum(raw_scores)
            matrix.append([score / score_total for score in raw_scores])

        transition_matrices.append(matrix)

    return transition_matrices
