"""IAT session scoring using the Greenwald et al. (2003) D2 convention.

The implemented D2 steps match the built-in error correction family used by
Project Implicit-style scoring:

1. Score only the combined-task blocks 3, 4, 6, and 7.
2. Discard combined-task trials whose final corrected latency exceeds 10,000 ms.
3. Reject completed sessions for which more than 10% of remaining combined-task
   trials are faster than 300 ms.
4. Discard remaining combined-task trials faster than 400 ms.
5. Compute two block-pair differences, each divided by its inclusive SD.
6. Average the two standardized pair scores into the final D-score.
"""

from __future__ import annotations

from statistics import mean, stdev

from apps.backend.domain.session.exceptions import SessionUnscoreableError
from apps.backend.models.scoring import (
    CompletedSessionSnapshot,
    SessionScoreResult,
    SessionScoringBlock,
    SessionScoringTrial,
)

FAST_TRIAL_EXCLUSION_THRESHOLD_MS = 300
FAST_TRIAL_TRIMMING_THRESHOLD_MS = 400
MAX_FAST_TRIAL_PROPORTION = 0.10
MAX_SCORABLE_LATENCY_MS = 10_000
MIN_POOLED_TRIAL_COUNT = 2
FIRST_LABEL_BLOCK_POSITION = 0
SECOND_LABEL_BLOCK_POSITION = 1
PRACTICE_PAIR_FIRST_BLOCK_POSITION = 2
PRACTICE_PAIR_SECOND_BLOCK_POSITION = 5
TEST_PAIR_FIRST_BLOCK_POSITION = 3
TEST_PAIR_SECOND_BLOCK_POSITION = 6
REQUIRED_BLOCK_COUNT = 7


def calculate_session_score(
    completed_session_snapshot: CompletedSessionSnapshot,
    little_to_no_association_upper_bound: float,
    slight_association_upper_bound: float,
    moderate_association_upper_bound: float,
) -> SessionScoreResult:
    """Compute one Greenwald et al. (2003) D2 IAT score and headline.

    Args:
        completed_session_snapshot: Completed session data required for scoring.
        little_to_no_association_upper_bound: Upper bound for neutral interpretation.
        slight_association_upper_bound: Upper bound for slight interpretation.
        moderate_association_upper_bound: Upper bound for moderate interpretation.

    Returns:
        The computed session score result.

    Raises:
        SessionUnscoreableError: The completed session cannot be scored.
    """
    if len(completed_session_snapshot.blocks) < REQUIRED_BLOCK_COUNT:
        raise SessionUnscoreableError("Completed sessions must include all scoring blocks.")

    practice_pair_first_block_latencies = _build_d2_block_latencies(
        completed_session_snapshot.blocks[PRACTICE_PAIR_FIRST_BLOCK_POSITION].trials
    )
    practice_pair_second_block_latencies = _build_d2_block_latencies(
        completed_session_snapshot.blocks[PRACTICE_PAIR_SECOND_BLOCK_POSITION].trials
    )
    test_pair_first_block_latencies = _build_d2_block_latencies(
        completed_session_snapshot.blocks[TEST_PAIR_FIRST_BLOCK_POSITION].trials
    )
    test_pair_second_block_latencies = _build_d2_block_latencies(
        completed_session_snapshot.blocks[TEST_PAIR_SECOND_BLOCK_POSITION].trials
    )
    _validate_d2_fast_trial_rate(
        [
            practice_pair_first_block_latencies,
            practice_pair_second_block_latencies,
            test_pair_first_block_latencies,
            test_pair_second_block_latencies,
        ]
    )
    practice_pair_score = _build_d_score_component(
        practice_pair_first_block_latencies,
        practice_pair_second_block_latencies,
    )
    test_pair_score = _build_d_score_component(
        test_pair_first_block_latencies,
        test_pair_second_block_latencies,
    )
    d_score = mean((practice_pair_score, test_pair_score))

    return SessionScoreResult(
        d_score=d_score,
        headline=_build_headline(
            completed_session_snapshot.blocks[FIRST_LABEL_BLOCK_POSITION],
            completed_session_snapshot.blocks[SECOND_LABEL_BLOCK_POSITION],
            d_score,
            little_to_no_association_upper_bound,
            slight_association_upper_bound,
            moderate_association_upper_bound,
        ),
    )


def _build_d2_block_latencies(trials: tuple[SessionScoringTrial, ...]) -> list[float]:
    if not trials:
        raise SessionUnscoreableError("Scored blocks must contain at least one completed trial.")

    block_latencies: list[float] = []
    for trial in trials:
        if not trial.events:
            raise SessionUnscoreableError("Completed scored trials must contain at least one event.")

        correct_event_index = next(
            (
                event_index
                for event_index, event in enumerate(trial.events)
                if event.event_type.value == trial.correct_response_side.value
            ),
            None,
        )
        if correct_event_index is None:
            raise SessionUnscoreableError("Completed session trials must end on the correct response side.")
        if correct_event_index != len(trial.events) - 1:
            raise SessionUnscoreableError(
                "Completed session trials must not contain events after the correct response."
            )

        final_latency_ms = trial.events[correct_event_index].elapsed_ms
        if final_latency_ms > MAX_SCORABLE_LATENCY_MS:
            continue

        block_latencies.append(float(final_latency_ms))

    if not block_latencies:
        raise SessionUnscoreableError("Each scored block must contain at least one scorable trial.")

    return block_latencies


def _validate_d2_fast_trial_rate(combined_block_latencies: list[list[float]]) -> None:
    remaining_latencies = [latency_ms for block_latencies in combined_block_latencies for latency_ms in block_latencies]
    if not remaining_latencies:
        raise SessionUnscoreableError("Completed sessions must contain scorable combined-task trials.")

    fast_trial_count = sum(latency_ms < FAST_TRIAL_EXCLUSION_THRESHOLD_MS for latency_ms in remaining_latencies)
    if fast_trial_count / len(remaining_latencies) > MAX_FAST_TRIAL_PROPORTION:
        raise SessionUnscoreableError("Completed sessions with too many sub-300 ms trials cannot be scored with D2.")


def _build_d_score_component(
    first_block_latencies: list[float],
    second_block_latencies: list[float],
) -> float:
    trimmed_first_block_latencies = [
        latency_ms for latency_ms in first_block_latencies if latency_ms >= FAST_TRIAL_TRIMMING_THRESHOLD_MS
    ]
    trimmed_second_block_latencies = [
        latency_ms for latency_ms in second_block_latencies if latency_ms >= FAST_TRIAL_TRIMMING_THRESHOLD_MS
    ]
    paired_latencies = [*trimmed_first_block_latencies, *trimmed_second_block_latencies]
    if len(paired_latencies) < MIN_POOLED_TRIAL_COUNT:
        raise SessionUnscoreableError("Each D-score block pair must contain at least two scored trials.")

    inclusive_sd = stdev(paired_latencies)
    if inclusive_sd == 0:
        raise SessionUnscoreableError("The session score is undefined for zero-variance block pairs.")

    if not trimmed_first_block_latencies or not trimmed_second_block_latencies:
        raise SessionUnscoreableError("Each D-score block must retain at least one trial after D2 trimming.")

    return (mean(trimmed_second_block_latencies) - mean(trimmed_first_block_latencies)) / inclusive_sd


def _build_headline(
    first_label_block: SessionScoringBlock,
    second_label_block: SessionScoringBlock,
    d_score: float,
    little_to_no_association_upper_bound: float,
    slight_association_upper_bound: float,
    moderate_association_upper_bound: float,
) -> str:
    if (
        len(first_label_block.left_labels) != 1
        or len(first_label_block.right_labels) != 1
        or len(second_label_block.left_labels) != 1
        or len(second_label_block.right_labels) != 1
    ):
        raise SessionUnscoreableError("Scoring blocks must each contain exactly one left and one right label.")

    absolute_d_score = abs(d_score)
    if absolute_d_score <= little_to_no_association_upper_bound:
        return "Little to no automatic association."
    if absolute_d_score <= slight_association_upper_bound:
        magnitude = "Slight"
    elif absolute_d_score <= moderate_association_upper_bound:
        magnitude = "Moderate"
    else:
        magnitude = "Strong"

    associated_first_label = first_label_block.left_labels[0] if d_score > 0 else first_label_block.right_labels[0]
    associated_second_label = second_label_block.left_labels[0] if d_score > 0 else second_label_block.right_labels[0]
    return f"{magnitude} automatic association of {associated_first_label} with {associated_second_label}."
