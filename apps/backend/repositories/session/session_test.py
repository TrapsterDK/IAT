"""Tests for session runtime repository behavior."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from apps.backend.domain.session.exceptions import (
    SessionConfigurationError,
    SessionConflictError,
    SessionInputError,
)
from apps.backend.models.session import (
    ClientContext,
    CompletedBlockInput,
    CompletedTrialInput,
    TrialEventInput,
    TrialEventType,
)
from apps.backend.repositories.session.conftest import build_repository_factory, build_run_plan, create_execution
from apps.backend.repositories.session.schema import SessionRecord, SessionTrialEventRecord
from apps.backend.repositories.session.session import SessionRepository

if TYPE_CHECKING:
    from pathlib import Path


def test_save_completed_block_accepts_same_payload_replay_after_stale_write_race(tmp_path: Path) -> None:
    # Given: one persisted session and two repositories that loaded it before the first upload commit.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()
        completed_block_input = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )

        with session_factory() as setup_session:
            create_execution(
                setup_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            setup_session.commit()

        first_session = session_factory()
        second_session = session_factory()
        try:
            first_repository = SessionRepository(first_session, session_key_factory=lambda: "unused")
            second_repository = SessionRepository(second_session, session_key_factory=lambda: "unused")

            # When: the first writer commits one accepted upload.
            first_repository.save_completed_block(
                "session-key",
                1,
                completed_block_input,
            )
            first_session.commit()

            # Then: the stale second writer treats the committed identical payload as one successful replay.
            second_repository.save_completed_block(
                "session-key",
                1,
                completed_block_input,
            )
        finally:
            first_session.close()
            second_session.close()
    finally:
        engine.dispose()


def test_save_completed_block_rejects_completed_session(tmp_path: Path) -> None:
    # Given: one persisted session whose root row is already marked completed.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()
        first_block_payload = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )
        completed_block_input = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=351),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )

        with session_factory() as database_session:
            created_state = create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            SessionRepository(database_session, session_key_factory=lambda: "unused").save_completed_block(
                "session-key",
                1,
                first_block_payload,
            )
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
                repository.save_completed_block("session-key", 1, completed_block_input)
    finally:
        engine.dispose()


def test_save_completed_block_rejects_replay_with_different_payload(tmp_path: Path) -> None:
    # Given: one running persisted session with one already committed first block upload.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()
        first_payload = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )
        conflicting_replay_payload = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=351),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )

        with session_factory() as database_session:
            create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")
            repository.save_completed_block("session-key", 1, first_payload)
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository receives one replay for the same committed block with different trial events.
            # Then: the conflicting replay is rejected as one invalid session-state transition.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
                repository.save_completed_block("session-key", 1, conflicting_replay_payload)
    finally:
        engine.dispose()


def test_create_execution_retries_session_key_collisions(tmp_path: Path) -> None:
    # Given: one existing session key and one factory that first collides and then yields one unique key.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()

        with session_factory() as database_session:
            create_execution(
                database_session,
                session_key_factory=lambda: "duplicate-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        with session_factory() as database_session:
            session_keys = iter(("duplicate-key", "retry-key"))

            # When: the repository creates one new session and retries after one key collision.
            created_state = create_execution(
                database_session,
                session_key_factory=lambda: next(session_keys),
                iat_slug="sample-iat",
                plan_seed=456,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
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
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()

        with session_factory() as database_session:
            create_execution(
                database_session,
                session_key_factory=lambda: "duplicate-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        # When: the repository exhausts its session-key collision retries.
        # Then: the repository raises one domain error instead of leaking one integrity exception.
        with (
            session_factory() as database_session,
            pytest.raises(
                SessionConfigurationError,
                match="The session could not be created because a unique session key was unavailable",
            ),
        ):
            create_execution(
                database_session,
                session_key_factory=lambda: "duplicate-key",
                iat_slug="sample-iat",
                plan_seed=456,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
    finally:
        engine.dispose()


def test_save_completed_block_persists_trial_events(tmp_path: Path) -> None:
    # Given: one running persisted session and one valid upload for its first configured block.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()

        with session_factory() as database_session:
            created_state = create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            repository.save_completed_block(
                "session-key",
                1,
                CompletedBlockInput(
                    trials=(
                        CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),
                        CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
                    )
                ),
            )
            database_session.commit()

        with session_factory() as database_session:
            persisted_session = database_session.get(SessionRecord, created_state.session_id)
            persisted_trial_events = tuple(
                database_session.scalars(
                    select(SessionTrialEventRecord)
                    .where(SessionTrialEventRecord.session_id == created_state.session_id)
                    .order_by(
                        SessionTrialEventRecord.block_index,
                        SessionTrialEventRecord.trial_index,
                        SessionTrialEventRecord.event_index,
                    )
                )
            )

            # When: the repository commits one full valid block upload.
            # Then: it persists the canonical trial events without completing the multi-block session.
            assert persisted_session is not None
            assert persisted_session.completed_at_utc is None
            assert [(event.trial_index, event.event_index, event.event_type) for event in persisted_trial_events] == [
                (1, 1, TrialEventType.LEFT),
                (2, 1, TrialEventType.RIGHT),
            ]
    finally:
        engine.dispose()


def test_save_completed_block_accepts_identical_final_block_replay_after_completion(tmp_path: Path) -> None:
    # Given: one persisted two-block session whose final block has already been committed.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()
        first_block_payload = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )
        final_block_payload = CompletedBlockInput(
            trials=(CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=450),)),)
        )

        with session_factory() as database_session:
            created_state = create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")
            repository.save_completed_block("session-key", 1, first_block_payload)
            repository.save_completed_block("session-key", 2, final_block_payload)
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository receives one identical retry for the already committed final block.
            repository.save_completed_block("session-key", 2, final_block_payload)
            database_session.commit()

            # Then: the replay succeeds without disturbing the completed session state.
            persisted_session = database_session.get(SessionRecord, created_state.session_id)
            assert persisted_session is not None
            assert persisted_session.completed_at_utc is not None
    finally:
        engine.dispose()


def test_save_completed_block_rejects_out_of_range_block_index(tmp_path: Path) -> None:
    # Given: one running persisted session and one positive block index beyond the configured plan.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()

        with session_factory() as database_session:
            create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository is asked to save one non-existent block.
            # Then: it rejects the invalid configured block reference before any write.
            with pytest.raises(SessionInputError, match="Block indexes must reference one configured run-plan block"):
                repository.save_completed_block(
                    "session-key",
                    999,
                    CompletedBlockInput(
                        trials=(
                            CompletedTrialInput(
                                events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)
                            ),
                        )
                    ),
                )
    finally:
        engine.dispose()


def test_save_completed_block_rejects_uploaded_trial_without_events(tmp_path: Path) -> None:
    # Given: one running persisted session and one upload containing one empty trial payload.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()

        with session_factory() as database_session:
            create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        with session_factory() as database_session:
            repository = SessionRepository(database_session, session_key_factory=lambda: "unused")

            # When: the repository validates one block containing one empty uploaded trial.
            # Then: it rejects the malformed raw trial payload before any write.
            with pytest.raises(SessionInputError, match="Uploaded trials must include at least one event"):
                repository.save_completed_block(
                    "session-key",
                    1,
                    CompletedBlockInput(
                        trials=(
                            CompletedTrialInput(events=()),
                            CompletedTrialInput(
                                events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)
                            ),
                        )
                    ),
                )
    finally:
        engine.dispose()
