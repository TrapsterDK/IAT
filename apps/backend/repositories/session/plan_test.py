"""Tests for session plan repository behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from apps.backend.models.session import ClientContext, SessionMode
from apps.backend.repositories.session.conftest import build_repository_factory, build_run_plan, create_execution
from apps.backend.repositories.session.schema import (
    SessionBlockLabelRecord,
    SessionBlockPlanRecord,
    SessionRecord,
    SessionTrialPlanRecord,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_create_execution_persists_full_run_plan_graph(tmp_path: Path) -> None:
    # Given: one empty session database and one deterministic run plan.
    engine, session_factory = build_repository_factory(tmp_path)

    try:
        run_plan = build_run_plan()

        # When: the repository creates one persisted execution.
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
