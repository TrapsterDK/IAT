"""Tests for session execution aggregate upload behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.backend.domain.session.exceptions import SessionConflictError, SessionInputError
from apps.backend.domain.session.execution import build_block_upload
from apps.backend.domain.session.models import (
    BlockPlan,
    BlockUploadInput,
    PlannedStimulus,
    ResponseSide,
    RunPlan,
    SessionUploadState,
    TrialEventType,
    TrialEventUploadInput,
    TrialPlan,
    TrialUploadInput,
)


def _build_run_plan() -> RunPlan:
    return RunPlan(
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
        blocks=(
            BlockPlan(
                left_labels=("Alpha",),
                right_labels=("Beta",),
                is_practice=True,
                trials=(
                    TrialPlan(
                        stimulus=PlannedStimulus(text="alpha"),
                        correct_response_side=ResponseSide.LEFT,
                    ),
                    TrialPlan(
                        stimulus=PlannedStimulus(text="beta"),
                        correct_response_side=ResponseSide.RIGHT,
                    ),
                ),
            ),
            BlockPlan(
                left_labels=("Good",),
                right_labels=("Bad",),
                is_practice=False,
                trials=(
                    TrialPlan(
                        stimulus=PlannedStimulus(text="good"),
                        correct_response_side=ResponseSide.LEFT,
                    ),
                ),
            ),
        ),
    )


def _build_session_upload_state(
    *,
    completed_at_utc: datetime | None = None,
    next_trial_id: int = 1,
    next_block_index: int = 1,
    next_event_index: int = 1,
) -> SessionUploadState:
    run_plan = _build_run_plan()
    return SessionUploadState(
        session_id=1,
        completed_at_utc=completed_at_utc,
        block_trial_counts=tuple(len(block.trials) for block in run_plan.blocks),
        next_trial_id=next_trial_id,
        next_block_index=next_block_index,
        next_event_index=next_event_index,
        anticipation_threshold_ms=run_plan.anticipation_threshold_ms,
        response_timeout_ms=run_plan.response_timeout_ms,
    )


def test_build_block_upload_derives_events() -> None:
    # Given: one running session and one complete upload for the first deterministic block.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(
            TrialUploadInput(
                events=(
                    TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=100),
                    TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),
                )
            ),
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
        )
    )

    # When: the first block upload is accepted.
    block_upload = build_block_upload(session_upload_state, 1, block_upload_input)

    # Then: the derived events keep deterministic trial and event indexes.
    assert block_upload.session_id == session_upload_state.session_id
    assert block_upload.completes_session is False
    assert [
        (event.trial_id, event.event_index, event.event_type, event.elapsed_ms) for event in block_upload.trial_events
    ] == [
        (1, 1, TrialEventType.LEFT, 100),
        (1, 2, TrialEventType.LEFT, 350),
        (2, 3, TrialEventType.RIGHT, 350),
    ]


def test_build_block_upload_derives_final_block_events() -> None:
    # Given: one running session with the first block already committed in deterministic order.
    session_upload_state = _build_session_upload_state(next_trial_id=3, next_block_index=2, next_event_index=3)
    block_upload_input = BlockUploadInput(
        trials=(TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: the final deterministic block is accepted.
    block_upload = build_block_upload(session_upload_state, 2, block_upload_input)

    # Then: the derived events continue the deterministic trial and event indexes.
    assert block_upload.completes_session is True
    assert [(event.trial_id, event.event_index) for event in block_upload.trial_events] == [(3, 3)]


def test_build_block_upload_rejects_partial_block_payload() -> None:
    # Given: one running session and one upload that only includes part of the first block.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: the partial upload is accepted.
    # Then: the aggregate rejects uploads that omit deterministic trials.
    with pytest.raises(SessionInputError, match="Uploaded blocks must include the full deterministic block payload"):
        build_block_upload(session_upload_state, 1, block_upload_input)


def test_build_block_upload_rejects_out_of_order_block() -> None:
    # Given: one running session waiting for the first block.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: the client uploads the second block first.
    # Then: the aggregate rejects the out-of-order upload.
    with pytest.raises(SessionConflictError, match="Uploaded blocks must be committed in deterministic run-plan order"):
        build_block_upload(session_upload_state, 2, block_upload_input)


def test_build_block_upload_rejects_trial_sequence_ending_with_anticipatory_response() -> None:
    # Given: one running session and one block whose first trial ends with one anticipatory response.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=100),)),
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
        )
    )

    # When: the block upload is accepted.
    # Then: the aggregate rejects incomplete trial event sequences.
    with pytest.raises(
        SessionInputError,
        match="Uploaded trial event sequences must end with one non-anticipatory response or timeout",
    ):
        build_block_upload(session_upload_state, 1, block_upload_input)


@pytest.mark.parametrize(
    ("event_type", "elapsed_ms", "expected_side", "expected_is_anticipatory"),
    [
        pytest.param(TrialEventType.LEFT, 100, ResponseSide.LEFT, True, id="anticipatory_left"),
        pytest.param(TrialEventType.RIGHT, 300, ResponseSide.RIGHT, False, id="non_anticipatory_right"),
    ],
)
def test_build_block_upload_keeps_raw_action_semantics(
    event_type: TrialEventType,
    elapsed_ms: int,
    expected_side: ResponseSide,
    expected_is_anticipatory: bool,
) -> None:
    # Given: one running session and one first-block upload containing one representative raw action.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(
            TrialUploadInput(
                events=(
                    TrialEventUploadInput(event_type=event_type, elapsed_ms=elapsed_ms),
                    TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),
                )
            ),
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
        )
    )

    # When: the first deterministic block is accepted.
    block_upload = build_block_upload(session_upload_state, 1, block_upload_input)

    # Then: the derived event keeps the raw action semantics and derived anticipation flag.
    first_event = block_upload.trial_events[0]
    assert first_event.event_type == event_type
    assert expected_side.value == event_type.value
    assert (first_event.elapsed_ms < session_upload_state.anticipation_threshold_ms) is expected_is_anticipatory


def test_build_block_upload_rejects_timeout_before_deadline() -> None:
    # Given: one running session and one uploaded timeout below the configured deadline.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.TIMEOUT, elapsed_ms=9_999),)),
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
        )
    )

    # When: the invalid timeout upload is accepted.
    # Then: the aggregate rejects timeouts below the configured response timeout.
    with pytest.raises(SessionInputError, match="Timeout events must meet the configured response timeout"):
        build_block_upload(session_upload_state, 1, block_upload_input)


def test_build_block_upload_rejects_timeout_before_final_event() -> None:
    # Given: one running session and one uploaded trial that records one timeout before another action.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(
            TrialUploadInput(
                events=(
                    TrialEventUploadInput(event_type=TrialEventType.TIMEOUT, elapsed_ms=10_000),
                    TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=9_900),
                )
            ),
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
        )
    )

    # When: the invalid sequence is accepted.
    # Then: timeout events are only allowed as the final event in one uploaded trial.
    with pytest.raises(SessionInputError, match="Timeout events must be the final event"):
        build_block_upload(session_upload_state, 1, block_upload_input)


def test_build_block_upload_rejects_out_of_range_block_index() -> None:
    # Given: one running session and one uploaded block payload.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: the client uploads one positive block index that does not exist in the deterministic run plan.
    # Then: the aggregate rejects the out-of-range block index instead of indexing into the run plan.
    with pytest.raises(SessionInputError, match="Block indexes must reference one configured run-plan block"):
        build_block_upload(session_upload_state, 999, block_upload_input)


def test_build_block_upload_rejects_uploaded_trial_without_events() -> None:
    # Given: one running session and one uploaded block containing one empty trial payload.
    session_upload_state = _build_session_upload_state()
    block_upload_input = BlockUploadInput(
        trials=(
            TrialUploadInput(events=()),
            TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
        )
    )

    # When: the invalid uploaded block is accepted.
    # Then: the aggregate rejects uploaded trials that contain no events instead of crashing.
    with pytest.raises(SessionInputError, match="Uploaded trials must include at least one event"):
        build_block_upload(session_upload_state, 1, block_upload_input)


def test_build_block_upload_rejects_completed_session() -> None:
    # Given: one session upload state that is already completed.
    session_upload_state = _build_session_upload_state(completed_at_utc=datetime.now(tz=UTC))
    block_upload_input = BlockUploadInput(
        trials=(TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: one more block upload is attempted.
    # Then: completed sessions reject later uploads.
    with pytest.raises(SessionConflictError, match="Only running sessions can accept block uploads"):
        build_block_upload(session_upload_state, 1, block_upload_input)
