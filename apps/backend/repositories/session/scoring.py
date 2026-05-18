"""Direct-SQL scoring repository for completed participant sessions."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import text

from apps.backend.domain.session.exceptions import SessionConflictError
from apps.backend.models.plan import ResponseSide
from apps.backend.models.scoring import (
    CompletedSessionSnapshot,
    SessionScoringBlock,
    SessionScoringEvent,
    SessionScoringTrial,
)
from apps.backend.models.session import TrialEventType

_SELECT_SESSION_CONTEXT_BY_KEY = text(
    """
    SELECT
        id,
        completed_at_utc
    FROM iat_sessions
    WHERE session_key = :session_key
    """
)

_SELECT_BLOCK_ROWS = text(
    """
    SELECT
        block_index,
        is_practice
    FROM iat_session_block_plans
    WHERE session_id = :session_id
    ORDER BY block_index
    """
)

_SELECT_LABEL_ROWS = text(
    """
    SELECT
        block_index,
        side,
        label
    FROM iat_session_block_labels
    WHERE session_id = :session_id
    ORDER BY block_index, side, label_index
    """
)

_SELECT_TRIAL_ROWS = text(
    """
    SELECT
        block_index,
        trial_index,
        correct_response_side
    FROM iat_session_trial_plans
    WHERE session_id = :session_id
    ORDER BY block_index, trial_index
    """
)

_SELECT_TRIAL_EVENT_ROWS = text(
    """
    SELECT
        block_index,
        trial_index,
        event_type,
        elapsed_ms
    FROM iat_session_trial_events
    WHERE session_id = :session_id
    ORDER BY block_index, trial_index, event_index
    """
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SessionScoringRepository:
    """Load completed-session scoring snapshots with direct SQL."""

    def __init__(self, database_session: Session) -> None:
        """Initialize one direct-SQL scoring repository.

        Args:
            database_session: Open database session used for score queries.
        """
        self._database_session = database_session

    def get_completed_session_snapshot_by_key(self, session_key: str) -> CompletedSessionSnapshot | None:
        """Load one completed-session scoring snapshot by public session key.

        Args:
            session_key: Opaque public session key.

        Returns:
            The completed session scoring snapshot, or `None` when unavailable.

        Raises:
            SessionConflictError: The stored session state cannot be scored.
        """
        session_row = (
            self._database_session.execute(
                _SELECT_SESSION_CONTEXT_BY_KEY,
                {"session_key": session_key},
            )
            .mappings()
            .one_or_none()
        )
        if session_row is None:
            return None

        if session_row["completed_at_utc"] is None:
            raise SessionConflictError("Only completed sessions can be scored.")

        session_id = session_row["id"]
        left_labels_by_block_index: dict[int, list[str]] = defaultdict(list)
        right_labels_by_block_index: dict[int, list[str]] = defaultdict(list)
        for row in self._database_session.execute(
            _SELECT_LABEL_ROWS,
            {"session_id": session_id},
        ).mappings():
            if row["side"] == ResponseSide.LEFT.value:
                left_labels_by_block_index[row["block_index"]].append(row["label"])
            else:
                right_labels_by_block_index[row["block_index"]].append(row["label"])

        events_by_trial_position: dict[tuple[int, int], list[SessionScoringEvent]] = defaultdict(list)
        for row in self._database_session.execute(
            _SELECT_TRIAL_EVENT_ROWS,
            {"session_id": session_id},
        ).mappings():
            events_by_trial_position[(row["block_index"], row["trial_index"])].append(
                SessionScoringEvent(
                    event_type=TrialEventType(row["event_type"]),
                    elapsed_ms=row["elapsed_ms"],
                )
            )

        trials_by_block_index: dict[int, list[SessionScoringTrial]] = defaultdict(list)
        for row in self._database_session.execute(
            _SELECT_TRIAL_ROWS,
            {"session_id": session_id},
        ).mappings():
            trials_by_block_index[row["block_index"]].append(
                SessionScoringTrial(
                    correct_response_side=ResponseSide(row["correct_response_side"]),
                    events=tuple(events_by_trial_position[(row["block_index"], row["trial_index"])]),
                )
            )

        return CompletedSessionSnapshot(
            blocks=tuple(
                SessionScoringBlock(
                    left_labels=tuple(left_labels_by_block_index[row["block_index"]]),
                    right_labels=tuple(right_labels_by_block_index[row["block_index"]]),
                    is_practice=bool(row["is_practice"]),
                    trials=tuple(trials_by_block_index[row["block_index"]]),
                )
                for row in self._database_session.execute(
                    _SELECT_BLOCK_ROWS,
                    {"session_id": session_id},
                ).mappings()
            ),
        )
