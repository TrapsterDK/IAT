"""Unit tests for session scoring."""

from backend.app.models import Response, Session
from backend.app.services.scoring import score_session

EXPECTED_TRIAL_COUNT = 2
EXPECTED_ACCURACY = 0.5
EXPECTED_MEAN_INITIAL_RT_MS = 450
EXPECTED_MEAN_COMPLETED_RT_MS = 550


def test_score_session_aggregates_relational_responses() -> None:
    """Scoring should aggregate accuracy and reaction times across responses."""
    experiment_session = Session(public_id="one", experiment_id=1, variant_id=1, seed=123)
    experiment_session.responses = [
        Response(
            block_id=1,
            stimulus_id=1,
            trial_index=0,
            expected_side="left",
            initial_actual_side="left",
            initial_key_used="e",
            initial_reaction_time_ms=400,
            completed_reaction_time_ms=400,
            correct_on_first_attempt=True,
            correction_count=0,
            stimulus_onset_ms=10,
            event_timestamp_ms=410,
            handler_timestamp_ms=410,
        ),
        Response(
            block_id=1,
            stimulus_id=2,
            trial_index=1,
            expected_side="right",
            initial_actual_side="left",
            initial_key_used="e",
            initial_reaction_time_ms=500,
            completed_reaction_time_ms=700,
            correct_on_first_attempt=False,
            correction_count=1,
            stimulus_onset_ms=20,
            event_timestamp_ms=520,
            handler_timestamp_ms=520,
        ),
    ]

    summary = score_session(experiment_session)

    if summary.trial_count != EXPECTED_TRIAL_COUNT:
        msg = "Expected the score summary to report both responses."
        raise AssertionError(msg)
    if summary.accuracy != EXPECTED_ACCURACY:
        msg = "Expected the score summary to calculate accuracy correctly."
        raise AssertionError(msg)
    if summary.mean_initial_reaction_time_ms != EXPECTED_MEAN_INITIAL_RT_MS:
        msg = "Expected the score summary to average initial reaction times."
        raise AssertionError(msg)
    if summary.mean_completed_reaction_time_ms != EXPECTED_MEAN_COMPLETED_RT_MS:
        msg = "Expected the score summary to average corrected reaction times."
        raise AssertionError(msg)
