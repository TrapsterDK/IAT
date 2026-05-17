"""Session upload transition logic for one persisted participant session."""

from __future__ import annotations

from apps.backend.domain.session.exceptions import (
    SessionConflictError,
    SessionInputError,
)
from apps.backend.domain.session.models import (
    BlockUpload,
    BlockUploadInput,
    SessionUploadState,
    TrialEvent,
    TrialEventType,
    TrialEventUploadInput,
)


def build_block_upload(
    session: SessionUploadState,
    block_index: int,
    block_upload_input: BlockUploadInput,
) -> BlockUpload:
    """Validate one block upload and derive the persisted event batch.

    Args:
        session: Validated persisted session upload state.
        block_index: One-based deterministic block index to upload.
        block_upload_input: Typed raw participant payload for that block.

    Returns:
        The validated block upload.
    """
    if block_index < 1:
        raise SessionInputError("Block indexes must be one-based positive integers.")

    if session.completed_at_utc is not None:
        raise SessionConflictError("Only running sessions can accept block uploads.")

    total_block_count = len(session.block_trial_counts)

    if block_index > total_block_count:
        raise SessionInputError("Block indexes must reference one configured run-plan block.")

    if block_index != session.next_block_index:
        raise SessionConflictError("Uploaded blocks must be committed in deterministic run-plan order.")

    if len(block_upload_input.trials) != session.block_trial_counts[block_index - 1]:
        raise SessionInputError("Uploaded blocks must include the full deterministic block payload.")

    return BlockUpload(
        session_id=session.session_id,
        trial_events=_build_block_upload_trial_events(
            block_upload_input=block_upload_input,
            next_trial_id=session.next_trial_id,
            next_event_index=session.next_event_index,
            anticipation_threshold_ms=session.anticipation_threshold_ms,
            response_timeout_ms=session.response_timeout_ms,
        ),
        completes_session=block_index == total_block_count,
    )


def _build_block_upload_trial_events(
    block_upload_input: BlockUploadInput,
    next_trial_id: int,
    next_event_index: int,
    anticipation_threshold_ms: int,
    response_timeout_ms: int,
) -> tuple[TrialEvent, ...]:
    derived_events: list[TrialEvent] = []
    for trial_offset, uploaded_trial in enumerate(block_upload_input.trials):
        derived_events.extend(
            _build_trial_events_for_trial_upload_input(
                trial_id=next_trial_id + trial_offset,
                trial_event_upload_inputs=uploaded_trial.events,
                next_event_index=next_event_index + len(derived_events),
                anticipation_threshold_ms=anticipation_threshold_ms,
                response_timeout_ms=response_timeout_ms,
            )
        )

    return tuple(derived_events)


def _build_trial_events_for_trial_upload_input(
    trial_id: int,
    trial_event_upload_inputs: tuple[TrialEventUploadInput, ...],
    next_event_index: int,
    anticipation_threshold_ms: int,
    response_timeout_ms: int,
) -> tuple[TrialEvent, ...]:
    if not trial_event_upload_inputs:
        raise SessionInputError("Uploaded trials must include at least one event.")

    derived_trial_events: list[TrialEvent] = []
    last_elapsed_ms = -1
    last_event_was_timeout = False
    for event_offset, trial_event_upload_input in enumerate(trial_event_upload_inputs):
        if last_event_was_timeout:
            raise SessionInputError("Timeout events must be the final event in one uploaded trial.")

        trial_event = _build_trial_event(
            trial_id=trial_id,
            event_index=next_event_index + event_offset,
            event_type=trial_event_upload_input.event_type,
            elapsed_ms=trial_event_upload_input.elapsed_ms,
            response_timeout_ms=response_timeout_ms,
        )
        last_event_was_timeout = trial_event.event_type is TrialEventType.TIMEOUT
        if trial_event.elapsed_ms < last_elapsed_ms:
            raise SessionInputError("Uploaded trial events must keep non-decreasing elapsed times.")

        derived_trial_events.append(trial_event)
        last_elapsed_ms = trial_event.elapsed_ms

    final_event = derived_trial_events[-1]
    if not last_event_was_timeout and final_event.elapsed_ms < anticipation_threshold_ms:
        raise SessionInputError(
            "Uploaded trial event sequences must end with one non-anticipatory response or timeout."
        )

    return tuple(derived_trial_events)


def _build_trial_event(
    trial_id: int,
    event_index: int,
    event_type: TrialEventType,
    elapsed_ms: int,
    response_timeout_ms: int,
) -> TrialEvent:
    if event_type is TrialEventType.TIMEOUT:
        if elapsed_ms < response_timeout_ms:
            raise SessionInputError("Timeout events must meet the configured response timeout.")
    elif elapsed_ms >= response_timeout_ms:
        raise SessionInputError("Timed-out trials must be submitted as timeout events.")

    return TrialEvent(
        trial_id=trial_id,
        event_index=event_index,
        elapsed_ms=elapsed_ms,
        event_type=event_type,
    )
