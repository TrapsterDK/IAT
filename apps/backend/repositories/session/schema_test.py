"""Tests for session repository schema constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from apps.backend.models.plan import ResponseSide
from apps.backend.models.session import ClientContext, SessionMode
from apps.backend.repositories.session.conftest import build_repository_factory, build_run_plan, create_execution
from apps.backend.repositories.session.schema import SessionBlockPlanRecord, SessionRecord, SessionTrialPlanRecord

if TYPE_CHECKING:
    from pathlib import Path


def test_trial_plan_rejects_duplicate_trial_index_in_same_block(tmp_path: Path) -> None:
    # Given: one persisted session whose first block already contains deterministic trial-plan rows.
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
                session_mode=SessionMode.PARTICIPANT,
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


def test_trial_plan_rejects_non_contiguous_block_indexes(tmp_path: Path) -> None:
    # Given: one persisted session whose stored block-plan key is tampered with directly.
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
                session_mode=SessionMode.PARTICIPANT,
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
