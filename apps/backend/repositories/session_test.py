"""Tests for the backend split session repositories."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.backend.database import create_database_schema, create_session_factory, create_sqlite_engine
from apps.backend.domain.session.exceptions import (
    SessionConfigurationError,
    SessionConflictError,
    SessionInputError,
)
from apps.backend.models.plan import BlockPlan, PlannedStimulus, ResponseSide, RunPlan, TrialPlan
from apps.backend.models.scoring import CompletedSessionSnapshot
from apps.backend.models.session import (
    ClientContext,
    CompletedBlockInput,
    CompletedTrialInput,
    SessionState,
    TrialEventInput,
    TrialEventType,
)
from apps.backend.repositories.session.plan import SessionPlanRepository
from apps.backend.repositories.session.schema import (
    SessionBlockLabelRecord,
    SessionBlockPlanRecord,
    SessionRecord,
    SessionTrialEventRecord,
    SessionTrialPlanRecord,
)
from apps.backend.repositories.session.scoring import SessionScoringRepository
from apps.backend.repositories.session.session import SessionRepository

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session, sessionmaker


def _create_execution(
    database_session: Session,
    session_key_factory: Callable[[], str],
    iat_slug: str,
    plan_seed: int,
    run_plan: RunPlan,
    client_context: ClientContext,
) -> SessionState:
    session_repository = SessionRepository(database_session, session_key_factory=session_key_factory)
    plan_repository = SessionPlanRepository(database_session)
    created_state = session_repository.create_session(
        iat_slug,
        plan_seed,
        client_context,
    )
    plan_repository.save_plan(created_state.session_id, run_plan)
    return created_state


def _get_completed_session_snapshot(database_session: Session, session_key: str) -> CompletedSessionSnapshot | None:
    return SessionScoringRepository(database_session).get_completed_session_snapshot_by_key(session_key)


def _build_run_plan() -> RunPlan:
    return RunPlan(
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


def _build_standard_score_run_plan() -> RunPlan:
    return RunPlan(
        blocks=(
            BlockPlan(
                left_labels=("Alpha",),
                right_labels=("Beta",),
                is_practice=True,
                trials=(
                    TrialPlan(stimulus=PlannedStimulus(text="alpha"), correct_response_side=ResponseSide.LEFT),
                    TrialPlan(stimulus=PlannedStimulus(text="beta"), correct_response_side=ResponseSide.RIGHT),
                ),
            ),
            BlockPlan(
                left_labels=("Gamma",),
                right_labels=("Delta",),
                is_practice=True,
                trials=(
                    TrialPlan(stimulus=PlannedStimulus(text="gamma"), correct_response_side=ResponseSide.LEFT),
                    TrialPlan(stimulus=PlannedStimulus(text="delta"), correct_response_side=ResponseSide.RIGHT),
                ),
            ),
            BlockPlan(
                left_labels=("Alpha", "Gamma"),
                right_labels=("Beta", "Delta"),
                is_practice=True,
                trials=(
                    TrialPlan(stimulus=PlannedStimulus(text="a1"), correct_response_side=ResponseSide.LEFT),
                    TrialPlan(stimulus=PlannedStimulus(text="b1"), correct_response_side=ResponseSide.RIGHT),
                ),
            ),
            BlockPlan(
                left_labels=("Alpha", "Gamma"),
                right_labels=("Beta", "Delta"),
                is_practice=False,
                trials=(
                    TrialPlan(stimulus=PlannedStimulus(text="a2"), correct_response_side=ResponseSide.LEFT),
                    TrialPlan(stimulus=PlannedStimulus(text="b2"), correct_response_side=ResponseSide.RIGHT),
                ),
            ),
            BlockPlan(
                left_labels=("Beta",),
                right_labels=("Alpha",),
                is_practice=True,
                trials=(
                    TrialPlan(stimulus=PlannedStimulus(text="beta-swap"), correct_response_side=ResponseSide.LEFT),
                    TrialPlan(stimulus=PlannedStimulus(text="alpha-swap"), correct_response_side=ResponseSide.RIGHT),
                ),
            ),
            BlockPlan(
                left_labels=("Beta", "Gamma"),
                right_labels=("Alpha", "Delta"),
                is_practice=True,
                trials=(
                    TrialPlan(stimulus=PlannedStimulus(text="b3"), correct_response_side=ResponseSide.LEFT),
                    TrialPlan(stimulus=PlannedStimulus(text="a3"), correct_response_side=ResponseSide.RIGHT),
                ),
            ),
            BlockPlan(
                left_labels=("Beta", "Gamma"),
                right_labels=("Alpha", "Delta"),
                is_practice=False,
                trials=(
                    TrialPlan(stimulus=PlannedStimulus(text="b4"), correct_response_side=ResponseSide.LEFT),
                    TrialPlan(stimulus=PlannedStimulus(text="a4"), correct_response_side=ResponseSide.RIGHT),
                ),
            ),
        ),
    )


def _append_single_event_trials(
    database_session: Session,
    session_id: int,
    block_trial_latencies: dict[int, tuple[int, ...]],
) -> None:
    for block_index, trial_latencies in block_trial_latencies.items():
        for trial_index, elapsed_ms in enumerate(trial_latencies, start=1):
            database_session.add(
                SessionTrialEventRecord(
                    session_id=session_id,
                    block_index=block_index,
                    trial_index=trial_index,
                    event_index=1,
                    elapsed_ms=elapsed_ms,
                    event_type=TrialEventType.LEFT if trial_index % 2 == 1 else TrialEventType.RIGHT,
                )
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
            created_state = _create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        # Then: the stored session keeps the complete block, label, and trial graph.
        with session_factory() as verify_session:
            persisted_session = verify_session.get(SessionRecord, created_state.session_id)
            persisted_block_plans = tuple(
                verify_session.scalars(
                    select(SessionBlockPlanRecord)
                    .where(SessionBlockPlanRecord.session_id == created_state.session_id)
                    .order_by(SessionBlockPlanRecord.block_index)
                )
            )
            persisted_block_labels = tuple(
                verify_session.scalars(
                    select(SessionBlockLabelRecord)
                    .where(SessionBlockLabelRecord.session_id == created_state.session_id)
                    .order_by(
                        SessionBlockLabelRecord.block_index,
                        SessionBlockLabelRecord.side,
                        SessionBlockLabelRecord.label_index,
                    )
                )
            )
            persisted_trial_plans = tuple(
                verify_session.scalars(
                    select(SessionTrialPlanRecord)
                    .where(SessionTrialPlanRecord.session_id == created_state.session_id)
                    .order_by(SessionTrialPlanRecord.block_index, SessionTrialPlanRecord.trial_index)
                )
            )

            assert persisted_session is not None
            assert persisted_session.session_key == "session-key"
            assert persisted_session.plan_seed == 123
            assert [(block.block_index, block.is_practice) for block in persisted_block_plans] == [
                (1, True),
                (2, False),
            ]
            assert [label.label for label in persisted_block_labels if label.block_index == 1] == ["Alpha", "Beta"]
            assert [trial.trial_index for trial in persisted_trial_plans if trial.block_index == 1] == [1, 2]
            assert [trial.trial_index for trial in persisted_trial_plans if trial.block_index == 2] == [1]
    finally:
        engine.dispose()


def test_save_completed_block_translates_stale_snapshot_write_conflict(tmp_path: Path) -> None:
    # Given: one persisted session and two repositories that loaded it before the first upload commit.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()
        completed_block_input = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )

        with session_factory() as setup_session:
            _create_execution(
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

            # Then: the stale second writer gets one session conflict instead of one raw integrity failure.
            with pytest.raises(
                SessionConflictError,
                match="The block upload could not be committed because the session state is invalid",
            ):
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


def test_trial_plan_rejects_duplicate_trial_index_in_same_block(tmp_path: Path) -> None:
    # Given: one persisted session whose first block already contains deterministic trial-plan rows.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            created_state = _create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.flush()

            persisted_session = database_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None

            first_block_plan = database_session.get(
                SessionBlockPlanRecord,
                {"session_id": persisted_session.id, "block_index": 1},
            )

            assert first_block_plan is not None

            # When: one duplicate trial index is inserted into the same persisted block.
            database_session.add(
                SessionTrialPlanRecord(
                    session_id=persisted_session.id,
                    block_index=first_block_plan.block_index,
                    trial_index=1,
                    stimulus_text="duplicate",
                    stimulus_image_path=None,
                    correct_response_side=ResponseSide.LEFT,
                )
            )

            # Then: the database rejects the duplicate composite trial identity.
            with pytest.raises(IntegrityError):
                database_session.flush()
    finally:
        engine.dispose()


def test_save_completed_block_rejects_completed_session(tmp_path: Path) -> None:
    # Given: one persisted session whose root row is already marked completed.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()
        completed_block_input = CompletedBlockInput(
            trials=(
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),
                CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.RIGHT, elapsed_ms=350),)),
            )
        )

        with session_factory() as database_session:
            created_state = _create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
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


def test_get_completed_session_snapshot_by_key_returns_completed_session_snapshot(tmp_path: Path) -> None:
    # Given: one completed seven-block session with persisted trial events for every scored trial.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_standard_score_run_plan()

        with session_factory() as database_session:
            created_state = _create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            persisted_session = database_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None

            _append_single_event_trials(
                database_session,
                persisted_session.id,
                {
                    1: (400, 400),
                    2: (410, 410),
                    3: (420, 420),
                    4: (430, 430),
                    5: (440, 440),
                    6: (700, 700),
                    7: (710, 710),
                },
            )
            persisted_session.completed_at_utc = persisted_session.created_at_utc.replace(tzinfo=UTC)
            database_session.commit()

        with session_factory() as database_session:
            # When: the scoring repository reconstructs one scoring aggregate for that completed session.
            completed_session_snapshot = _get_completed_session_snapshot(database_session, "session-key")

            # Then: the aggregate contains the persisted blocks, trials, and trial events.
            assert isinstance(completed_session_snapshot, CompletedSessionSnapshot)
            assert completed_session_snapshot.blocks[0].left_labels == ("Alpha",)
            assert completed_session_snapshot.blocks[0].right_labels == ("Beta",)
            assert completed_session_snapshot.blocks[1].left_labels == ("Gamma",)
            assert completed_session_snapshot.blocks[1].right_labels == ("Delta",)
            assert completed_session_snapshot.blocks[4].left_labels == ("Beta",)
            assert completed_session_snapshot.blocks[4].right_labels == ("Alpha",)
            assert completed_session_snapshot.blocks[2].trials[0].correct_response_side is ResponseSide.LEFT
            assert [event.elapsed_ms for event in completed_session_snapshot.blocks[2].trials[0].events] == [420]
            assert completed_session_snapshot.blocks[6].trials[1].events[0].event_type is TrialEventType.RIGHT
    finally:
        engine.dispose()


def test_get_completed_session_snapshot_by_key_rejects_running_session(tmp_path: Path) -> None:
    # Given: one persisted session that has not completed yet.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_standard_score_run_plan()

        with session_factory() as database_session:
            _create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            database_session.commit()

        # When: the scoring repository is asked for one score aggregate before completion.
        # Then: the running session is rejected as unscoreable.
        with (
            session_factory() as database_session,
            pytest.raises(
                SessionConflictError,
                match="Only completed sessions can be scored",
            ),
        ):
            _get_completed_session_snapshot(database_session, "session-key")
    finally:
        engine.dispose()


def test_create_execution_retries_session_key_collisions(tmp_path: Path) -> None:
    # Given: one existing session key and one factory that first collides and then yields one unique key.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            _create_execution(
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
            created_state = _create_execution(
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
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            _create_execution(
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
            _create_execution(
                database_session,
                session_key_factory=lambda: "duplicate-key",
                iat_slug="sample-iat",
                plan_seed=456,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
    finally:
        engine.dispose()


def test_trial_plan_rejects_non_contiguous_block_indexes(tmp_path: Path) -> None:
    # Given: one persisted session whose stored block-plan key is tampered with directly.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            created_state = _create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
            )
            persisted_session = database_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None

            # When: one child key is changed so it no longer points at one persisted block plan.
            # Then: the database rejects the broken composite foreign key immediately.
            persisted_trial_plan = database_session.get(
                SessionTrialPlanRecord,
                {"session_id": persisted_session.id, "block_index": 1, "trial_index": 1},
            )

            assert persisted_trial_plan is not None

            persisted_trial_plan.block_index = 3
            with pytest.raises(IntegrityError):
                database_session.commit()
    finally:
        engine.dispose()


def test_save_completed_block_persists_trial_events(tmp_path: Path) -> None:
    # Given: one running persisted session and one valid upload for its first configured block.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            created_state = _create_execution(
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


def test_save_completed_block_rejects_out_of_range_block_index(tmp_path: Path) -> None:
    # Given: one running persisted session and one positive block index beyond the configured plan.
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            _create_execution(
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
    engine, session_factory = _build_repository_factory(tmp_path)

    try:
        run_plan = _build_run_plan()

        with session_factory() as database_session:
            _create_execution(
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
