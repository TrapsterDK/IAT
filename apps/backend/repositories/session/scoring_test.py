"""Tests for session scoring repository behavior."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

import pytest

from apps.backend.domain.session.exceptions import SessionConflictError
from apps.backend.models.plan import ResponseSide
from apps.backend.models.session import ClientContext, SessionMode, TrialEventType
from apps.backend.repositories.session.conftest import (
    append_single_event_trials,
    build_repository_factory,
    build_standard_score_run_plan,
    create_execution,
    get_completed_session_snapshot,
)
from apps.backend.repositories.session.schema import SessionRecord

if TYPE_CHECKING:
    from pathlib import Path


def test_get_completed_session_snapshot_by_key_returns_completed_session_snapshot(tmp_path: Path) -> None:
    # Given: one completed seven-block session with persisted trial events for every scored trial.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_standard_score_run_plan()

        with session_factory() as database_session:
            created_state = create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
                session_mode=SessionMode.PARTICIPANT,
            )
            persisted_session = database_session.get(SessionRecord, created_state.session_id)

            assert persisted_session is not None

            append_single_event_trials(
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
            completed_session_snapshot = get_completed_session_snapshot(database_session, "session-key")

            # Then: the aggregate contains the persisted blocks, trials, and trial events.
            assert completed_session_snapshot is not None
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
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_standard_score_run_plan()

        with session_factory() as database_session:
            create_execution(
                database_session,
                session_key_factory=lambda: "session-key",
                iat_slug="sample-iat",
                plan_seed=123,
                run_plan=run_plan,
                client_context=ClientContext(),
                session_mode=SessionMode.PARTICIPANT,
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
            get_completed_session_snapshot(database_session, "session-key")
    finally:
        engine.dispose()
