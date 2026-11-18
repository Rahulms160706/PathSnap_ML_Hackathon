from src.decoder.transition_model import build_transition_probabilities
from src.decoder.viterbi_decoder import decode_viterbi


def _as_list(value, name: str) -> list:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a sequence")
    try:
        return list(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a sequence") from exc


def decode_candidate_sequence(
    candidate_groups,
    emission_probability_groups,
    observation_coordinates,
    arc_endpoint_mapping,
    node_coordinates,
) -> dict:
    """
    Build geometry-based transitions and decode ordered candidate groups.

    Candidate IDs and emission probabilities must have matching group and
    within-group order. Coordinates are passed unchanged to the transition
    model, which expects (latitude, longitude).
    """
    candidate_groups = _as_list(candidate_groups, "candidate_groups")
    emission_probability_groups = _as_list(
        emission_probability_groups,
        "emission_probability_groups",
    )

    if not candidate_groups:
        raise ValueError("At least one observation must be provided")
    if len(candidate_groups) != len(emission_probability_groups):
        raise ValueError(
            "candidate_groups and emission_probability_groups must contain "
            "the same number of observations"
        )

    ordered_candidate_groups = []
    ordered_emission_groups = []
    for observation_index, (candidate_group, emission_group) in enumerate(
        zip(candidate_groups, emission_probability_groups)
    ):
        candidates = _as_list(
            candidate_group,
            f"candidate_groups[{observation_index}]",
        )
        emissions = _as_list(
            emission_group,
            f"emission_probability_groups[{observation_index}]",
        )

        if not candidates:
            raise ValueError(
                f"candidate_groups[{observation_index}] must not be empty"
            )
        if len(candidates) != len(emissions):
            raise ValueError(
                f"candidate_groups[{observation_index}] and "
                f"emission_probability_groups[{observation_index}] must have "
                "the same length"
            )

        ordered_candidate_groups.append(candidates)
        ordered_emission_groups.append(emissions)

    transition_probabilities = build_transition_probabilities(
        candidate_groups=ordered_candidate_groups,
        observation_coordinates=observation_coordinates,
        arc_endpoint_mapping=arc_endpoint_mapping,
        node_coordinates=node_coordinates,
    )
    result = decode_viterbi(
        candidate_ids=ordered_candidate_groups,
        emission_probabilities=ordered_emission_groups,
        transition_probabilities=transition_probabilities,
    )
    return {
        **result,
        "decoder_name": "geometry_viterbi",
    }
