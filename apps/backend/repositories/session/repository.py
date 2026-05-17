"""Persistence repository for SQL-backed IAT sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only

from apps.backend.domain.session.exceptions import (
    SessionConfigurationError,
    SessionConflictError,
    SessionNotFoundError,
)
from apps.backend.domain.session.models import (
    BlockUpload,
    ClientContext,
    RunPlan,
    SessionState,
    SessionUploadState,
    TrialEvent,
    TrialEventType,
)
from apps.backend.repositories.session.schema import (
    BlockLabelSide,
    SessionBlockLabelRecord,
    SessionBlockPlanRecord,
    SessionRecord,
    SessionTrialEventRecord,
    SessionTrialPlanRecord,
)

SESSION_KEY_COLLISION_RETRY_COUNT = 3

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session


class SessionRepository:
    """Persist and read SQL-backed participant session state."""

    def __init__(self, database_session: Session, session_key_factory: Callable[[], str]) -> None:
        """Initialize the repository for one live database session.

        Args:
            database_session: Existing SQLAlchemy session used for reads and writes.
            session_key_factory: Callable used to generate public session keys.
        """
        self._database_session = database_session
        self._session_key_factory = session_key_factory

    def create_execution(
        self,
        iat_slug: str,
        plan_seed: int,
        run_plan: RunPlan,
        client_context: ClientContext,
    ) -> SessionState:
        """Persist one new running session and its immutable run plan.

        Args:
            iat_slug: Published IAT slug associated with the session.
            plan_seed: Random seed used to generate the run plan.
            run_plan: Deterministic plan snapshot assigned to the session.
            client_context: Client metadata captured at session creation.

        Returns:
            The newly persisted session state.
        """
        created_at_utc = datetime.now(tz=UTC)
        for _ in range(SESSION_KEY_COLLISION_RETRY_COUNT):
            session_record = SessionRecord(
                session_key=self._session_key_factory(),
                iat_slug=iat_slug,
                plan_seed=plan_seed,
                anticipation_threshold_ms=run_plan.anticipation_threshold_ms,
                response_timeout_ms=run_plan.response_timeout_ms,
                created_at_utc=created_at_utc,
                user_agent=client_context.user_agent,
                platform=client_context.platform,
                viewport_width_px=client_context.viewport_width_px,
                viewport_height_px=client_context.viewport_height_px,
                device_pixel_ratio=client_context.device_pixel_ratio,
            )
            savepoint = self._database_session.begin_nested()
            try:
                self._database_session.add(session_record)
                self._database_session.flush()
            except IntegrityError:
                savepoint.rollback()
            else:
                savepoint.commit()
                break
        else:
            raise SessionConfigurationError(
                "The session could not be created because a unique session key was unavailable."
            )

        session_record.block_plans.extend(_build_block_plan_records(session_record.id, run_plan))
        self._database_session.flush()
        return _build_session_state(session_record)

    def get_upload_state_by_key(self, session_key: str) -> SessionUploadState | None:
        """Load one lightweight session upload aggregate by public session key.

        Args:
            session_key: Opaque public session key.

        Returns:
            The validated session upload state, or `None` when unavailable.
        """
        session_record = self._database_session.scalar(
            select(SessionRecord)
            .where(SessionRecord.session_key == session_key)
            .options(
                load_only(
                    SessionRecord.id,
                    SessionRecord.session_key,
                    SessionRecord.created_at_utc,
                    SessionRecord.completed_at_utc,
                    SessionRecord.anticipation_threshold_ms,
                    SessionRecord.response_timeout_ms,
                ),
            )
        )
        if session_record is None:
            return None

        block_trial_counts = _build_block_trial_counts(
            tuple(
                self._database_session.execute(
                    select(SessionBlockPlanRecord.block_index, func.count(SessionTrialPlanRecord.id))
                    .outerjoin(
                        SessionTrialPlanRecord, SessionTrialPlanRecord.block_plan_id == SessionBlockPlanRecord.id
                    )
                    .where(SessionBlockPlanRecord.session_id == session_record.id)
                    .group_by(SessionBlockPlanRecord.id, SessionBlockPlanRecord.block_index)
                    .order_by(SessionBlockPlanRecord.block_index)
                ).tuples()
            )
        )
        trial_events = tuple(
            _build_trial_event(record)
            for record in self._database_session.scalars(
                select(SessionTrialEventRecord)
                .where(SessionTrialEventRecord.session_id == session_record.id)
                .options(
                    load_only(
                        SessionTrialEventRecord.trial_id,
                        SessionTrialEventRecord.event_index,
                        SessionTrialEventRecord.elapsed_ms,
                        SessionTrialEventRecord.event_type,
                    )
                )
                .order_by(SessionTrialEventRecord.event_index)
            )
        )

        return _build_session_upload_state(session_record, block_trial_counts, trial_events)

    def commit_block_upload(self, block_upload: BlockUpload) -> None:
        """Persist one validated block upload.

        Args:
            block_upload: Validated block upload ready to persist.

        """
        session_id = block_upload.session_id
        session_record = self._database_session.get(SessionRecord, session_id)
        if session_record is None:
            raise SessionNotFoundError(f"IAT session not found: {session_id}")

        if session_record.completed_at_utc is not None:
            raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

        event_records_to_append = _build_event_records(session_id, block_upload.trial_events)

        try:
            self._database_session.add_all(event_records_to_append)
            if block_upload.completes_session:
                session_record.completed_at_utc = datetime.now(tz=UTC)
            self._database_session.flush()
        except IntegrityError as exc:
            raise SessionConflictError(
                "The block upload could not be committed because the session state is invalid."
            ) from exc


def _build_session_state(session_record: SessionRecord) -> SessionState:
    return SessionState(
        session_id=session_record.id,
        session_key=session_record.session_key,
        created_at_utc=session_record.created_at_utc,
        completed_at_utc=session_record.completed_at_utc,
    )


def _build_session_upload_state(
    session_record: SessionRecord,
    block_trial_counts: tuple[int, ...],
    trial_events: tuple[TrialEvent, ...],
) -> SessionUploadState:
    next_trial_id, next_block_index, next_event_index = _analyze_stored_trial_history(
        block_trial_counts,
        trial_events,
        anticipation_threshold_ms=session_record.anticipation_threshold_ms,
        response_timeout_ms=session_record.response_timeout_ms,
    )
    total_block_count = len(block_trial_counts)
    is_history_exhausted = next_block_index == total_block_count + 1
    if session_record.completed_at_utc is None and is_history_exhausted:
        raise SessionConflictError("The block upload could not be committed because the session state is invalid.")
    if session_record.completed_at_utc is not None and not is_history_exhausted:
        raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

    return SessionUploadState(
        session_id=session_record.id,
        completed_at_utc=session_record.completed_at_utc,
        block_trial_counts=block_trial_counts,
        next_trial_id=next_trial_id,
        next_block_index=next_block_index,
        next_event_index=next_event_index,
        anticipation_threshold_ms=session_record.anticipation_threshold_ms,
        response_timeout_ms=session_record.response_timeout_ms,
    )


def _build_trial_event(trial_event_record: SessionTrialEventRecord) -> TrialEvent:
    return TrialEvent(
        trial_id=trial_event_record.trial_id,
        event_index=trial_event_record.event_index,
        elapsed_ms=trial_event_record.elapsed_ms,
        event_type=trial_event_record.event_type,
    )


def _build_event_records(session_id: int, trial_events: tuple[TrialEvent, ...]) -> list[SessionTrialEventRecord]:
    return [
        SessionTrialEventRecord(
            session_id=session_id,
            trial_id=trial_event.trial_id,
            event_index=trial_event.event_index,
            elapsed_ms=trial_event.elapsed_ms,
            event_type=trial_event.event_type,
        )
        for trial_event in trial_events
    ]


def _build_block_trial_counts(block_rows: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    if not block_rows:
        raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

    block_trial_counts: list[int] = []
    expected_block_index = 1
    for block_index, trial_count in block_rows:
        if block_index != expected_block_index or trial_count < 1:
            raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

        block_trial_counts.append(trial_count)
        expected_block_index += 1

    return tuple(block_trial_counts)


def _analyze_stored_trial_history(
    block_trial_counts: tuple[int, ...],
    trial_events: tuple[TrialEvent, ...],
    anticipation_threshold_ms: int,
    response_timeout_ms: int,
) -> tuple[int, int, int]:
    if anticipation_threshold_ms < 0 or response_timeout_ms <= 0 or anticipation_threshold_ms >= response_timeout_ms:
        raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

    total_trial_count = sum(block_trial_counts)
    next_expected_event_index = 1
    current_trial_id = 1
    saw_history = False
    current_trial_events: list[TrialEvent] = []

    for trial_event in trial_events:
        if trial_event.event_index != next_expected_event_index or not 1 <= trial_event.trial_id <= total_trial_count:
            raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

        if not saw_history:
            if trial_event.trial_id != current_trial_id:
                raise SessionConflictError("The block upload could not be committed because the session state is invalid.")
            saw_history = True
        elif trial_event.trial_id == current_trial_id + 1:
            if not current_trial_events or (
                current_trial_events[-1].event_type is not TrialEventType.TIMEOUT
                and current_trial_events[-1].elapsed_ms < anticipation_threshold_ms
            ):
                raise SessionConflictError("The block upload could not be committed because the session state is invalid.")
            current_trial_id = trial_event.trial_id
            current_trial_events = []
        elif trial_event.trial_id != current_trial_id:
            raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

        if current_trial_events and (
            current_trial_events[-1].event_type is TrialEventType.TIMEOUT
            or trial_event.elapsed_ms < current_trial_events[-1].elapsed_ms
        ):
            raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

        if (trial_event.event_type is TrialEventType.TIMEOUT and trial_event.elapsed_ms < response_timeout_ms) or (
            trial_event.event_type is not TrialEventType.TIMEOUT and trial_event.elapsed_ms >= response_timeout_ms
        ):
            raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

        current_trial_events.append(trial_event)
        next_expected_event_index += 1

    completed_trial_count = 0
    if saw_history and (
        not current_trial_events
        or (
            current_trial_events[-1].event_type is not TrialEventType.TIMEOUT
            and current_trial_events[-1].elapsed_ms < anticipation_threshold_ms
        )
    ):
        raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

    if saw_history:
        completed_trial_count = current_trial_id

    accepted_block_count = _count_accepted_blocks(block_trial_counts, completed_trial_count)
    next_block_index = accepted_block_count + 1
    return completed_trial_count + 1, next_block_index, next_expected_event_index


def _count_accepted_blocks(block_trial_counts: tuple[int, ...], completed_trial_count: int) -> int:
    if completed_trial_count == 0:
        return 0

    consumed_trials = 0
    for accepted_block_count, block_trial_count in enumerate(block_trial_counts, start=1):
        consumed_trials += block_trial_count
        if completed_trial_count == consumed_trials:
            return accepted_block_count
        if completed_trial_count < consumed_trials:
            raise SessionConflictError("The block upload could not be committed because the session state is invalid.")

    raise SessionConflictError("The block upload could not be committed because the session state is invalid.")


def _build_block_plan_records(session_id: int, run_plan: RunPlan) -> tuple[SessionBlockPlanRecord, ...]:
    built_blocks = []
    trial_id = 1
    for block_index, block in enumerate(run_plan.blocks, start=1):
        built_blocks.append(
            SessionBlockPlanRecord(
                session_id=session_id,
                block_index=block_index,
                is_practice=block.is_practice,
                labels=[
                    SessionBlockLabelRecord(
                        side=side,
                        label_index=label_index,
                        label=label,
                    )
                    for side, labels in (
                        (BlockLabelSide.LEFT, block.left_labels),
                        (BlockLabelSide.RIGHT, block.right_labels),
                    )
                    for label_index, label in enumerate(labels, start=1)
                ],
                trial_plans=[
                    SessionTrialPlanRecord(
                        session_id=session_id,
                        trial_id=trial_id + trial_index_in_block - 1,
                        trial_index_in_block=trial_index_in_block,
                        stimulus_text=trial.stimulus.text,
                        stimulus_image_path=(
                            None if trial.stimulus.image_path is None else trial.stimulus.image_path.as_posix()
                        ),
                        correct_response_side=trial.correct_response_side,
                    )
                    for trial_index_in_block, trial in enumerate(block.trials, start=1)
                ],
            )
        )
        trial_id += len(block.trials)

    return tuple(built_blocks)
