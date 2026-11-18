import math
from typing import Iterable, Sequence


def _as_list(value: Iterable, name: str) -> list:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain sequences, not a scalar string or bytes")
    try:
        return list(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be iterable") from exc


def _validate_probability(value, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number between 0 and 1")
    try:
        probability = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number between 0 and 1") from exc
    if not math.isfinite(probability) or probability < 0.0 or probability > 1.0:
        raise ValueError(f"{name} must be a finite number between 0 and 1")
    return probability


def _log_probability(probability: float) -> float:
    return -math.inf if probability == 0.0 else math.log(probability)


def decode_viterbi(
    candidate_ids: Sequence[Sequence],
    emission_probabilities: Sequence[Sequence[float]],
    transition_probabilities: Sequence[Sequence[Sequence[float]]],
) -> dict:
    """
    Decode the most likely candidate sequence with Viterbi in log space.

    This function has no road-network assumptions. Transition matrices are
    supplied externally and preserve the candidate order for each observation.
    """
    observations = _as_list(candidate_ids, "candidate_ids")
    emissions = _as_list(emission_probabilities, "emission_probabilities")
    transitions = _as_list(transition_probabilities, "transition_probabilities")

    if not observations:
        raise ValueError("At least one observation must be provided")
    if len(emissions) != len(observations):
        raise ValueError(
            "candidate_ids and emission_probabilities must contain "
            "the same number of observations"
        )
    if len(transitions) != len(observations) - 1:
        raise ValueError(
            "transition_probabilities must contain one matrix for every "
            "pair of consecutive observations"
        )

    candidate_states = []
    emission_values = []

    for observation_index, (observation_candidates, observation_emissions) in enumerate(
        zip(observations, emissions)
    ):
        states = _as_list(
            observation_candidates,
            f"candidate_ids[{observation_index}]",
        )
        probabilities = _as_list(
            observation_emissions,
            f"emission_probabilities[{observation_index}]",
        )

        if not states:
            raise ValueError(
                f"candidate_ids[{observation_index}] must contain at least one candidate"
            )
        if len(states) != len(probabilities):
            raise ValueError(
                f"candidate_ids[{observation_index}] and "
                f"emission_probabilities[{observation_index}] must have the same length"
            )

        validated_emissions = [
            _validate_probability(
                probability,
                f"emission_probabilities[{observation_index}][{state_index}]",
            )
            for state_index, probability in enumerate(probabilities)
        ]
        candidate_states.append(states)
        emission_values.append(validated_emissions)

    scores = [
        _log_probability(probability)
        for probability in emission_values[0]
    ]
    backpointers = []

    for observation_index in range(1, len(observations)):
        matrix = _as_list(
            transitions[observation_index - 1],
            f"transition_probabilities[{observation_index - 1}]",
        )
        previous_count = len(candidate_states[observation_index - 1])
        current_count = len(candidate_states[observation_index])

        if len(matrix) != previous_count:
            raise ValueError(
                f"transition_probabilities[{observation_index - 1}] must have "
                f"{previous_count} rows"
            )

        validated_matrix = []
        for previous_index, row in enumerate(matrix):
            row_values = _as_list(
                row,
                f"transition_probabilities[{observation_index - 1}]"
                f"[{previous_index}]",
            )
            if len(row_values) != current_count:
                raise ValueError(
                    f"transition_probabilities[{observation_index - 1}] must have "
                    f"{previous_count} rows and {current_count} columns"
                )

            validated_row = [
                _validate_probability(
                    probability,
                    f"transition_probabilities[{observation_index - 1}]"
                    f"[{previous_index}][{current_index}]",
                )
                for current_index, probability in enumerate(row_values)
            ]
            validated_matrix.append(validated_row)

        new_scores = []
        current_backpointers = []

        for current_index in range(current_count):
            best_previous_index = 0
            best_score = -math.inf

            for previous_index in range(previous_count):
                transition_log_probability = _log_probability(
                    validated_matrix[previous_index][current_index]
                )
                candidate_score = (
                    scores[previous_index]
                    + transition_log_probability
                )
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_previous_index = previous_index

            new_scores.append(
                best_score
                + _log_probability(emission_values[observation_index][current_index])
            )
            current_backpointers.append(best_previous_index)

        scores = new_scores
        backpointers.append(current_backpointers)

    best_final_index = max(range(len(scores)), key=lambda index: scores[index])
    best_final_score = scores[best_final_index]
    if not math.isfinite(best_final_score):
        raise ValueError(
            "No possible path exists because all path probabilities are zero"
        )

    selected_indices = [best_final_index]
    for pointers in reversed(backpointers):
        selected_indices.append(pointers[selected_indices[-1]])
    selected_indices.reverse()

    selected_ids = [
        candidate_states[observation_index][state_index]
        for observation_index, state_index in enumerate(selected_indices)
    ]

    return {
        "selected_candidate_ids": selected_ids,
        "selected_candidate_indices": selected_indices,
        "final_best_log_probability": best_final_score,
        "number_of_observations": len(observations),
    }
