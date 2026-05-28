"""Tests for improved IAT session scoring."""

from __future__ import annotations

from statistics import mean, stdev

import pytest

from apps.backend.domain.session.exceptions import SessionUnscoreableError
from apps.backend.domain.session.scoring import calculate_session_score
from apps.backend.models.plan import ResponseSide
from apps.backend.models.scoring import (
    CompletedSessionSnapshot,
    SessionScoringBlock,
    SessionScoringEvent,
    SessionScoringTrial,
)
from apps.backend.models.session import TrialEventType

LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND = 0.15
SLIGHT_ASSOCIATION_UPPER_BOUND = 0.35
MODERATE_ASSOCIATION_UPPER_BOUND = 0.65


def _build_trial(
    correct_response_side: ResponseSide,
    final_latency_ms: float,
    *,
    wrong_before_final: bool = False,
    wrong_after_final: bool = False,
    wrong_final: bool = False,
) -> SessionScoringTrial:
    wrong_event_type = TrialEventType.RIGHT if correct_response_side is ResponseSide.LEFT else TrialEventType.LEFT
    final_event_type = wrong_event_type if wrong_final else TrialEventType(correct_response_side.value)
    base_events = (
        (
            SessionScoringEvent(event_type=wrong_event_type, elapsed_ms=final_latency_ms - 100),
            SessionScoringEvent(event_type=final_event_type, elapsed_ms=final_latency_ms),
        )
        if wrong_before_final
        else (SessionScoringEvent(event_type=final_event_type, elapsed_ms=final_latency_ms),)
    )
    events = (
        (
            *base_events,
            SessionScoringEvent(event_type=wrong_event_type, elapsed_ms=final_latency_ms + 100),
        )
        if wrong_after_final
        else base_events
    )
    return SessionScoringTrial(
        correct_response_side=correct_response_side,
        events=events,
    )


def _build_snapshot(
    *,
    block_latencies: dict[int, tuple[float, float]],
    error_block_index: int | None = None,
    wrong_after_final_block_index: int | None = None,
    wrong_final_block_index: int | None = None,
) -> CompletedSessionSnapshot:
    return CompletedSessionSnapshot(
        blocks=(
            SessionScoringBlock(
                left_labels=("Alpha",),
                right_labels=("Beta",),
                is_practice=True,
                trials=(),
            ),
            SessionScoringBlock(
                left_labels=("Gamma",),
                right_labels=("Delta",),
                is_practice=True,
                trials=(),
            ),
            SessionScoringBlock(
                left_labels=("Alpha", "Gamma"),
                right_labels=("Beta", "Delta"),
                is_practice=True,
                trials=(
                    _build_trial(
                        ResponseSide.LEFT,
                        block_latencies[3][0],
                        wrong_before_final=error_block_index == 3,
                        wrong_after_final=wrong_after_final_block_index == 3,
                        wrong_final=wrong_final_block_index == 3,
                    ),
                    _build_trial(ResponseSide.RIGHT, block_latencies[3][1]),
                ),
            ),
            SessionScoringBlock(
                left_labels=("Alpha", "Gamma"),
                right_labels=("Beta", "Delta"),
                is_practice=False,
                trials=(
                    _build_trial(
                        ResponseSide.LEFT,
                        block_latencies[4][0],
                        wrong_before_final=error_block_index == 4,
                        wrong_after_final=wrong_after_final_block_index == 4,
                        wrong_final=wrong_final_block_index == 4,
                    ),
                    _build_trial(ResponseSide.RIGHT, block_latencies[4][1]),
                ),
            ),
            SessionScoringBlock(
                left_labels=("Beta",),
                right_labels=("Alpha",),
                is_practice=True,
                trials=(
                    _build_trial(ResponseSide.LEFT, 450),
                    _build_trial(ResponseSide.RIGHT, 460),
                ),
            ),
            SessionScoringBlock(
                left_labels=("Beta", "Gamma"),
                right_labels=("Alpha", "Delta"),
                is_practice=True,
                trials=(
                    _build_trial(
                        ResponseSide.LEFT,
                        block_latencies[6][0],
                        wrong_before_final=error_block_index == 6,
                        wrong_after_final=wrong_after_final_block_index == 6,
                        wrong_final=wrong_final_block_index == 6,
                    ),
                    _build_trial(ResponseSide.RIGHT, block_latencies[6][1]),
                ),
            ),
            SessionScoringBlock(
                left_labels=("Beta", "Gamma"),
                right_labels=("Alpha", "Delta"),
                is_practice=False,
                trials=(
                    _build_trial(
                        ResponseSide.LEFT,
                        block_latencies[7][0],
                        wrong_before_final=error_block_index == 7,
                        wrong_after_final=wrong_after_final_block_index == 7,
                        wrong_final=wrong_final_block_index == 7,
                    ),
                    _build_trial(ResponseSide.RIGHT, block_latencies[7][1]),
                ),
            ),
        ),
    )


def test_calculate_session_score_returns_neutral_headline_for_balanced_latencies() -> None:
    # Given: one completed session whose D2-scored combined blocks have matching latencies.
    scoring_data = _build_snapshot(
        block_latencies={
            3: (500, 520),
            4: (530, 550),
            6: (500, 520),
            7: (530, 550),
        }
    )

    # When: the improved D-score is computed.
    score_result = calculate_session_score(
        scoring_data,
        LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND,
        SLIGHT_ASSOCIATION_UPPER_BOUND,
        MODERATE_ASSOCIATION_UPPER_BOUND,
    )

    # Then: the D-score is neutral and the headline stays non-directional.
    assert score_result.d_score == pytest.approx(0.0)
    assert score_result.headline == "Little to no automatic association."


def test_calculate_session_score_uses_latency_until_correct_response() -> None:
    # Given: one completed session whose first reversed-practice trial includes one corrected error.
    scoring_data = _build_snapshot(
        block_latencies={
            3: (400, 400),
            4: (410, 410),
            6: (500, 500),
            7: (520, 520),
        },
        error_block_index=6,
    )
    expected_block_3_mean = mean((400.0, 400.0))
    expected_block_6_mean = mean((500.0, 500.0))
    expected_block_4_mean = mean((410.0, 410.0))
    expected_block_7_mean = mean((520.0, 520.0))
    expected_practice_component = (expected_block_6_mean - expected_block_3_mean) / stdev((400.0, 400.0, 500.0, 500.0))
    expected_test_component = (expected_block_7_mean - expected_block_4_mean) / stdev((410.0, 410.0, 520.0, 520.0))

    # When: the Greenwald et al. (2003) D2 score is computed.
    score_result = calculate_session_score(
        scoring_data,
        LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND,
        SLIGHT_ASSOCIATION_UPPER_BOUND,
        MODERATE_ASSOCIATION_UPPER_BOUND,
    )

    # Then: the corrected trial keeps its latency-to-correct instead of using one computed penalty.
    assert score_result.d_score == pytest.approx((expected_practice_component + expected_test_component) / 2)
    assert score_result.headline == "Strong automatic association of Alpha with Gamma."


def test_calculate_session_score_discards_trials_over_ten_seconds() -> None:
    # Given: one completed session whose final combined block contains one trial beyond the D2 upper bound.
    scoring_data = _build_snapshot(
        block_latencies={
            3: (500, 520),
            4: (530, 550),
            6: (560, 580),
            7: (600, 10_001),
        },
    )
    expected_practice_component = (mean((560.0, 580.0)) - mean((500.0, 520.0))) / stdev((500.0, 520.0, 560.0, 580.0))
    expected_test_component = (600.0 - mean((530.0, 550.0))) / stdev((530.0, 550.0, 600.0))

    # When: the Greenwald et al. (2003) D2 score is computed.
    score_result = calculate_session_score(
        scoring_data,
        LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND,
        SLIGHT_ASSOCIATION_UPPER_BOUND,
        MODERATE_ASSOCIATION_UPPER_BOUND,
    )

    # Then: trials above 10,000 ms are discarded before block-pair scoring.
    assert score_result.d_score == pytest.approx((expected_practice_component + expected_test_component) / 2)
    assert score_result.headline == "Strong automatic association of Alpha with Gamma."


def test_calculate_session_score_rejects_trials_that_end_on_the_wrong_side() -> None:
    # Given: one completed session whose final reversed-practice response ends on the wrong side.
    scoring_data = _build_snapshot(
        block_latencies={
            3: (500, 520),
            4: (530, 550),
            6: (560, 580),
            7: (600, 620),
        },
        wrong_final_block_index=6,
    )

    # When: the improved D-score is computed.
    # Then: sessions that never end on the correct side are rejected as invalid.
    with pytest.raises(SessionUnscoreableError, match="correct response side"):
        calculate_session_score(
            scoring_data,
            LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND,
            SLIGHT_ASSOCIATION_UPPER_BOUND,
            MODERATE_ASSOCIATION_UPPER_BOUND,
        )


def test_calculate_session_score_rejects_trials_with_events_after_correct_response() -> None:
    # Given: one completed session whose corrected trial records one later stray response.
    scoring_data = _build_snapshot(
        block_latencies={
            3: (500, 520),
            4: (530, 550),
            6: (560, 580),
            7: (600, 620),
        },
        wrong_after_final_block_index=6,
    )

    # When: the improved D-score is computed.
    # Then: trials with any events after the correct response are rejected as invalid.
    with pytest.raises(SessionUnscoreableError, match="events after the correct response"):
        calculate_session_score(
            scoring_data,
            LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND,
            SLIGHT_ASSOCIATION_UPPER_BOUND,
            MODERATE_ASSOCIATION_UPPER_BOUND,
        )


def test_calculate_session_score_rejects_sessions_with_too_many_sub_300_ms_trials() -> None:
    # Given: one completed session whose combined-task trials exceed the D2 fast-trial exclusion rate.
    scoring_data = _build_snapshot(
        block_latencies={
            3: (250, 250),
            4: (410, 420),
            6: (500, 510),
            7: (520, 530),
        },
    )

    # When: the Greenwald et al. (2003) D2 score is computed.
    # Then: sessions with more than 10% sub-300 ms trials are rejected.
    with pytest.raises(SessionUnscoreableError, match="sub-300 ms"):
        calculate_session_score(
            scoring_data,
            LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND,
            SLIGHT_ASSOCIATION_UPPER_BOUND,
            MODERATE_ASSOCIATION_UPPER_BOUND,
        )


def test_calculate_session_score_discards_trials_faster_than_400_ms_after_fast_trial_check() -> None:
    # Given: one completed session with one sub-400 ms trial that does not exceed the D2 exclusion-rate threshold.
    scoring_data = _build_snapshot(
        block_latencies={
            3: (350, 520),
            4: (530, 550),
            6: (560, 580),
            7: (600, 620),
        }
    )
    expected_practice_component = (mean((560.0, 580.0)) - 520.0) / stdev((520.0, 560.0, 580.0))
    expected_test_component = (mean((600.0, 620.0)) - mean((530.0, 550.0))) / stdev((530.0, 550.0, 600.0, 620.0))

    # When: the Greenwald et al. (2003) D2 score is computed.
    score_result = calculate_session_score(
        scoring_data,
        LITTLE_TO_NO_ASSOCIATION_UPPER_BOUND,
        SLIGHT_ASSOCIATION_UPPER_BOUND,
        MODERATE_ASSOCIATION_UPPER_BOUND,
    )

    # Then: trials faster than 400 ms are trimmed from the pairwise D2 computation.
    assert score_result.d_score == pytest.approx((expected_practice_component + expected_test_component) / 2)
