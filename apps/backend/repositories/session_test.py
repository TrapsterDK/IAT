"""Tests for the backend SQL-backed session repository."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from apps.backend.database import create_database_schema, create_session_factory, create_sqlite_engine
from apps.backend.domain.session.exceptions import (
    SessionConfigurationError,
    SessionConflictError,
)
from apps.backend.domain.session.models import (
    BlockPlan,
    BlockUpload,
    ClientContext,
    PlannedStimulus,
    ResponseSide,
    RunPlan,
    TrialEvent,
    TrialEventType,
    TrialPlan,
)
from apps.backend.repositories.session.repository import SessionRepository
from apps.backend.repositories.session.schema import SessionRecord, SessionTrialEventRecord, SessionTrialPlanRecord

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session, sessionmaker


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


def _build_repository_factory(tmp_path: Path) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_sqlite_engine(tmp_path / "instance/session-repository.sqlite3")
    create_database_schema(engine)
    return engine, create_session_factory(engine)


def test_create_execution_persists_full_run_plan_graph(tmp_path: Path) -> None:
    # Given: one empty session database and one deterministic run plan.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        # When: the repository creates one persisted execution.
        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "session-key")
            created_state = repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            database_session.commit()

        # Then: the stored session keeps the complete block, label, and trial graph.
        with session_factory() as verify_session:
            persisted_session = verify_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None
            assert persisted_session.session_key == "session-key"
            assert persisted_session.plan_seed == 123
            assert [(block.block_index, block.is_practice) for block in persisted_session.block_plans] == [
                (1, True),
                (2, False),
            ]
            assert [label.label for label in persisted_session.block_plans[0].labels] == ["Alpha", "Beta"]
            assert [trial.trial_id for trial in persisted_session.block_plans[0].trial_plans] == [1, 2]
            assert [trial.trial_id for trial in persisted_session.block_plans[1].trial_plans] == [3]
    finally:
        engine.dispose()


def test_commit_block_upload_translates_stale_snapshot_write_conflict(tmp_path: Path) -> None:
    # Given: one persisted session and two repositories that loaded it before the first upload commit.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()
        trial_events = (
            TrialEvent(trial_id=1, event_index=1, elapsed_ms=350, event_type=TrialEventType.LEFT),
            TrialEvent(trial_id=2, event_index=2, elapsed_ms=350, event_type=TrialEventType.RIGHT),
        )

        with session_factory() as setup_session:
            setup_repository = SessionRepository(setup_session, session_key_factory=lambda: "session-key")
            created_state = setup_repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            setup_session.commit()

        first_session = session_factory()
        second_session = session_factory()
        try:
            first_repository = SessionRepository(first_session, session_key_factory=lambda: "unused")
            second_repository = SessionRepository(second_session, session_key_factory=lambda: "unused")

            # When: the first writer commits one accepted upload.
            first_session_upload_state = first_repository.get_upload_state_by_key("session-key")
            second_session_upload_state = second_repository.get_upload_state_by_key("session-key")

            assert first_session_upload_state is not None
            assert second_session_upload_state is not None

            first_repository.commit_block_upload(
                BlockUpload(session_id=created_state.session_id, trial_events=trial_events, completes_session=False)
            )
            first_session.commit()

            # Then: the stale second writer gets one session conflict instead of one raw integrity failure.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
                second_repository.commit_block_upload(
                    BlockUpload(session_id=created_state.session_id, trial_events=trial_events, completes_session=False)
                )
        finally:
            first_session.close()
            second_session.close()
    finally:
        engine.dispose()


def test_trial_plan_must_belong_to_same_session_as_block_plan(tmp_path: Path) -> None:
    # Given: two persisted sessions with distinct block-plan rows.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            session_keys = iter(("session-key-1", "session-key-2"))
            repository = SessionRepository(database_session, session_key_factory=lambda: next(session_keys))
            first_state = repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            second_state = repository.create_execution("sample-iat", 456, run_plan, ClientContext())
            database_session.flush()

            first_session_record = database_session.get(SessionRecord, first_state.session_id)
            second_session_record = database_session.get(SessionRecord, second_state.session_id)

            assert first_session_record is not None
            assert second_session_record is not None

            first_block_plan = first_session_record.block_plans[0]

            # When: one trial plan row is inserted for the second session but points at the first session's block plan.
            database_session.add(
                SessionTrialPlanRecord(
                    session_id=second_session_record.id,
                    block_plan_id=first_block_plan.id,
                    trial_id=999,
                    trial_index_in_block=99,
                    stimulus_text="mismatched",
                    stimulus_image_path=None,
                    correct_response_side=ResponseSide.LEFT,
                )
            )

            # Then: the database rejects the cross-session block-plan reference.
            with pytest.raises(IntegrityError):
                database_session.flush()
    finally:
        engine.dispose()


def test_commit_block_upload_rejects_completed_session(tmp_path: Path) -> None:
    # Given: one persisted session whose root row is already marked completed.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()
        trial_events = (
            TrialEvent(trial_id=1, event_index=1, elapsed_ms=350, event_type=TrialEventType.LEFT),
            TrialEvent(trial_id=2, event_index=2, elapsed_ms=350, event_type=TrialEventType.RIGHT),
        )

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "session-key")
            created_state = repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            persisted_session = database_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None

            persisted_session.completed_at_utc = persisted_session.created_at_utc.replace(tzinfo=UTC)
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository is asked to append one more block upload after completion.
            # Then: the impossible write is rejected before any append occurs.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
                repository.commit_block_upload(
                    BlockUpload(session_id=created_state.session_id, trial_events=trial_events, completes_session=False)
                )
    finally:
        engine.dispose()


def test_create_execution_retries_session_key_collisions(tmp_path: Path) -> None:
    # Given: one existing session key and one factory that first collides and then yields one unique key.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "duplicate-key")
            repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            database_session.commit()

        with session_factory() as database_session:
            session_keys = iter(("duplicate-key", "retry-key"))
            repository = SessionRepository(database_session, session_key_factory=lambda: next(session_keys))

            # When: the repository creates one new session and retries after one key collision.
            created_state = repository.create_execution("sample-iat", 456, run_plan, ClientContext())
            database_session.commit()

            # Then: the repository persists the new session with the next generated unique key.
            assert created_state.session_key == "retry-key"
            persisted_session = database_session.get(SessionRecord, created_state.session_id)
            assert persisted_session is not None
            assert persisted_session.session_key == "retry-key"
    finally:
        engine.dispose()


def test_create_execution_raises_session_creation_error_after_repeated_key_collisions(tmp_path: Path) -> None:
    # Given: one existing session key and one factory that never produces one unique replacement key.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "duplicate-key")
            repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "duplicate-key")

            # When: the repository exhausts its session-key collision retries.
            # Then: the repository raises one domain error instead of leaking one integrity exception.
            with pytest.raises(
                SessionConfigurationError,
                match="The session could not be created because a unique session key was unavailable",
            ):
                repository.create_execution("sample-iat", 456, run_plan, ClientContext())
    finally:
        engine.dispose()


def test_get_upload_state_by_key_rejects_non_contiguous_block_indexes(tmp_path: Path) -> None:
    # Given: one persisted session whose stored block indexes no longer form one contiguous run-plan order.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "session-key")
            created_state = repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            persisted_session = database_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None

            persisted_session.block_plans[1].block_index = 3
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: one upload aggregate is loaded from that malformed stored block graph.
            # Then: the repository rejects the invalid persisted session state.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
                repository.get_upload_state_by_key("session-key")
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "trial_events",
    [
        pytest.param(
            (TrialEvent(trial_id=2, event_index=1, elapsed_ms=350, event_type=TrialEventType.RIGHT),),
            id="history_starts_at_wrong_trial",
        ),
        pytest.param(
            (
                TrialEvent(trial_id=1, event_index=1, elapsed_ms=350, event_type=TrialEventType.LEFT),
                TrialEvent(trial_id=1, event_index=2, elapsed_ms=300, event_type=TrialEventType.LEFT),
                TrialEvent(trial_id=2, event_index=3, elapsed_ms=350, event_type=TrialEventType.RIGHT),
            ),
            id="decreasing_elapsed_within_trial",
        ),
        pytest.param(
            (
                TrialEvent(trial_id=1, event_index=1, elapsed_ms=10_000, event_type=TrialEventType.TIMEOUT),
                TrialEvent(trial_id=1, event_index=2, elapsed_ms=10_001, event_type=TrialEventType.RIGHT),
                TrialEvent(trial_id=2, event_index=3, elapsed_ms=350, event_type=TrialEventType.RIGHT),
            ),
            id="timeout_not_final_event",
        ),
    ],
)
def test_get_upload_state_by_key_rejects_invalid_stored_history(
    tmp_path: Path,
    trial_events: tuple[TrialEvent, ...],
) -> None:
    # Given: one persisted session whose stored event history violates one repository invariant.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "session-key")
            created_state = repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            database_session.flush()

            for trial_event in trial_events:
                database_session.add(
                    SessionTrialEventRecord(
                        session_id=created_state.session_id,
                        trial_id=trial_event.trial_id,
                        event_index=trial_event.event_index,
                        elapsed_ms=trial_event.elapsed_ms,
                        event_type=trial_event.event_type,
                    )
                )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository reconstructs the upload state from the malformed history.
            # Then: the invalid stored history is rejected at the repository boundary.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
                repository.get_upload_state_by_key("session-key")
    finally:
        engine.dispose()


def test_get_upload_state_by_key_rejects_exhausted_history_on_running_session(tmp_path: Path) -> None:
    # Given: one running persisted session whose stored event history already covers the full run plan.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "session-key")
            created_state = repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            database_session.flush()
            for trial_id, event_type in ((1, TrialEventType.LEFT), (2, TrialEventType.RIGHT), (3, TrialEventType.LEFT)):
                database_session.add(
                    SessionTrialEventRecord(
                        session_id=created_state.session_id,
                        trial_id=trial_id,
                        event_index=trial_id,
                        elapsed_ms=350,
                        event_type=event_type,
                    )
                )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository reconstructs the upload state for that impossible running session.
            # Then: the exhausted running history is rejected at the repository boundary.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
                repository.get_upload_state_by_key("session-key")
    finally:
        engine.dispose()


def test_get_upload_state_by_key_rejects_completed_session_with_incomplete_history(tmp_path: Path) -> None:
    # Given: one completed persisted session whose stored event history does not cover the full run plan.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "session-key")
            created_state = repository.create_execution("sample-iat", 123, run_plan, ClientContext())
            database_session.commit()

        with session_factory() as database_session:
            persisted_session = database_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None

            persisted_session.completed_at_utc = persisted_session.created_at_utc.replace(tzinfo=UTC)
            for trial_id, event_type in ((1, TrialEventType.LEFT), (2, TrialEventType.RIGHT)):
                database_session.add(
                    SessionTrialEventRecord(
                        session_id=created_state.session_id,
                        trial_id=trial_id,
                        event_index=trial_id,
                        elapsed_ms=350,
                        event_type=event_type,
                    )
                )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository reconstructs the upload state for that inconsistent completed session.
            # Then: the incomplete completed state is rejected at the repository boundary.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
                repository.get_upload_state_by_key("session-key")
    finally:
        engine.dispose()
