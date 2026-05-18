"""Direct-SQL repository for persisted IAT session run plans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from apps.backend.models.plan import ResponseSide

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from apps.backend.models.plan import RunPlan

_INSERT_BLOCK_PLAN = text(
    """
    INSERT INTO iat_session_block_plans (
        session_id,
        block_index,
        is_practice
    ) VALUES (
        :session_id,
        :block_index,
        :is_practice
    )
    """
)

_INSERT_BLOCK_LABEL = text(
    """
    INSERT INTO iat_session_block_labels (
        session_id,
        block_index,
        side,
        label_index,
        label
    ) VALUES (
        :session_id,
        :block_index,
        :side,
        :label_index,
        :label
    )
    """
)

_INSERT_TRIAL_PLAN = text(
    """
    INSERT INTO iat_session_trial_plans (
        session_id,
        block_index,
        trial_index,
        stimulus_text,
        stimulus_image_path,
        correct_response_side
    ) VALUES (
        :session_id,
        :block_index,
        :trial_index,
        :stimulus_text,
        :stimulus_image_path,
        :correct_response_side
    )
    """
)


class SessionPlanRepository:
    """Persist one immutable run-plan snapshot for one created session."""

    def __init__(self, database_session: Session) -> None:
        """Initialize one direct-SQL session-plan repository.

        Args:
            database_session: Open database session used for plan writes.
        """
        self._database_session = database_session

    def save_plan(self, session_id: int, run_plan: RunPlan) -> None:
        """Persist one immutable deterministic run plan for one session.

        Args:
            session_id: Persisted session identifier that owns the run plan.
            run_plan: Deterministic run-plan snapshot to persist.
        """
        block_plan_rows = [
            {
                "session_id": session_id,
                "block_index": block_index,
                "is_practice": block.is_practice,
            }
            for block_index, block in enumerate(run_plan.blocks, start=1)
        ]
        block_label_rows = [
            {
                "session_id": session_id,
                "block_index": block_index,
                "side": side,
                "label_index": label_index,
                "label": label,
            }
            for block_index, block in enumerate(run_plan.blocks, start=1)
            for side, labels in (
                (ResponseSide.LEFT, block.left_labels),
                (ResponseSide.RIGHT, block.right_labels),
            )
            for label_index, label in enumerate(labels, start=1)
        ]
        trial_plan_rows = [
            {
                "session_id": session_id,
                "block_index": block_index,
                "trial_index": trial_index,
                "stimulus_text": trial.stimulus.text,
                "stimulus_image_path": None
                if trial.stimulus.image_path is None
                else trial.stimulus.image_path.as_posix(),
                "correct_response_side": trial.correct_response_side.value,
            }
            for block_index, block in enumerate(run_plan.blocks, start=1)
            for trial_index, trial in enumerate(block.trials, start=1)
        ]

        if block_plan_rows:
            self._database_session.execute(
                _INSERT_BLOCK_PLAN,
                block_plan_rows,
            )
        if block_label_rows:
            self._database_session.execute(
                _INSERT_BLOCK_LABEL,
                block_label_rows,
            )
        if trial_plan_rows:
            self._database_session.execute(
                _INSERT_TRIAL_PLAN,
                trial_plan_rows,
            )
