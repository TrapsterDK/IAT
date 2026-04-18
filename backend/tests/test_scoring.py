"""Unit tests for attempt scoring."""

from backend.app.models import (
    Attempt,
    Category,
    Experiment,
    ExperimentVariant,
    Phase,
    ResponseSide,
    Showing,
    ShowingInput,
    Stimulus,
)
from backend.app.services.scoring import score_attempt

EXPECTED_SHOWING_COUNT = 2
EXPECTED_ACCURACY = 0.5
EXPECTED_MEAN_INITIAL_RT_MS = 450
EXPECTED_MEAN_COMPLETED_RT_MS = 550


def test_score_attempt_aggregates_relational_showings() -> None:
    """Scoring should aggregate accuracy and reaction times across showings."""
    test = Experiment(slug="demo", title="Demo", description="Demo")
    variant = ExperimentVariant(
        test_id=1,
        key_event_mode="keydown",
        preload_assets=True,
        inter_trial_interval_ms=150,
        response_timeout_ms=5000,
    )
    flowers = Category(test_id=1, code="flowers", label="Flowers")
    insects = Category(test_id=1, code="insects", label="Insects")
    test.categories = [flowers, insects]
    phase = Phase(
        test_id=1,
        sequence_number=1,
        showings_per_category=1,
        left_primary_category_id=1,
        left_secondary_category_id=None,
        right_primary_category_id=2,
        right_secondary_category_id=None,
        congruency=None,
    )
    phase.left_primary_category = flowers
    phase.right_primary_category = insects
    stimulus_left = Stimulus(category_id=1, text_value="rose", asset_path=None)
    stimulus_left.category = flowers
    stimulus_right = Stimulus(category_id=2, text_value="wasp", asset_path=None)
    stimulus_right.category = insects

    attempt = Attempt(
        public_id="one",
        variant_id=1,
        visibility_interruptions=0,
    )
    attempt.variant = variant
    attempt.showings = [
        Showing(
            phase_id=1,
            stimulus_id=1,
            showing_index=0,
            stimulus_onset_ms=10,
            phase=phase,
            stimulus=stimulus_left,
            inputs=[
                ShowingInput(
                    input_index=0,
                    side=ResponseSide.LEFT,
                    input_source="keyboard",
                    event_timestamp_ms=410,
                    handler_timestamp_ms=410,
                )
            ],
        ),
        Showing(
            phase_id=1,
            stimulus_id=2,
            showing_index=1,
            stimulus_onset_ms=20,
            phase=phase,
            stimulus=stimulus_right,
            inputs=[
                ShowingInput(
                    input_index=0,
                    side=ResponseSide.LEFT,
                    input_source="keyboard",
                    event_timestamp_ms=520,
                    handler_timestamp_ms=520,
                ),
                ShowingInput(
                    input_index=1,
                    side=ResponseSide.RIGHT,
                    input_source="keyboard",
                    event_timestamp_ms=720,
                    handler_timestamp_ms=720,
                ),
            ],
        ),
    ]

    summary = score_attempt(attempt)

    if summary.showing_count != EXPECTED_SHOWING_COUNT:
        raise AssertionError("Expected the score summary to report both showings.")
    if summary.accuracy != EXPECTED_ACCURACY:
        raise AssertionError("Expected the score summary to calculate accuracy correctly.")
    if summary.mean_initial_reaction_time_ms != EXPECTED_MEAN_INITIAL_RT_MS:
        raise AssertionError("Expected the score summary to average initial reaction times.")
    if summary.mean_completed_reaction_time_ms != EXPECTED_MEAN_COMPLETED_RT_MS:
        raise AssertionError("Expected the score summary to average completed reaction times.")
