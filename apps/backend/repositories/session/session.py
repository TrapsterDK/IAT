"""Direct-SQL repository for persisted IAT session runtime state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError

from apps.backend.domain.session.exceptions import (
    INVALID_SESSION_STATE_MESSAGE,
    SessionConfigurationError,
    SessionConflictError,
    SessionInputError,
    SessionNotFoundError,
)
from apps.backend.models.session import (
    ClientContext,
    CompletedBlockInput,
    SessionState,
)
from libs.sqlalchemy.types import UtcDateTime

SESSION_KEY_COLLISION_RETRY_COUNT = 3

_INSERT_SESSION = text(
    """
    INSERT INTO iat_sessions (
        session_key,
        iat_slug,
        plan_seed,
        created_at_utc,
        user_agent,
        platform,
        viewport_width_px,
        viewport_height_px,
        device_pixel_ratio
    ) VALUES (
        :session_key,
        :iat_slug,
        :plan_seed,
        :created_at_utc,
        :user_agent,
        :platform,
        :viewport_width_px,
        :viewport_height_px,
        :device_pixel_ratio
    )
    RETURNING id
    """
).bindparams(bindparam("created_at_utc", type_=UtcDateTime()))

_INSERT_TRIAL_EVENT = text(
    """
    INSERT INTO iat_session_trial_events (
        session_id,
        block_index,
        trial_index,
        event_index,
        elapsed_ms,
        event_type
    ) VALUES (
        :session_id,
        :block_index,
        :trial_index,
        :event_index,
        :elapsed_ms,
        :event_type
    )
    """
)

_SELECT_UPLOAD_CONTEXT_BY_KEY = text(
    """
    SELECT
        id,
        completed_at_utc
    FROM iat_sessions
    WHERE session_key = :session_key
    """
)

_SELECT_BLOCK_UPLOAD_FACTS = text(
    """
    SELECT
        COUNT(*) AS trial_count,
        EXISTS(
            SELECT 1
            FROM iat_session_block_plans
            WHERE session_id = :session_id AND block_index > :block_index
        ) AS has_later_blocks,
        (
            SELECT COUNT(DISTINCT block_index)
            FROM iat_session_trial_events
            WHERE session_id = :session_id
        ) AS uploaded_block_count
    FROM iat_session_trial_plans
    WHERE session_id = :session_id AND block_index = :block_index
    """
)

_MARK_SESSION_COMPLETED = text(
    """
    UPDATE iat_sessions
    SET completed_at_utc = :completed_at_utc
    WHERE id = :session_id AND completed_at_utc IS NULL
    """
).bindparams(bindparam("completed_at_utc", type_=UtcDateTime()))

_SELECT_BLOCK_TRIAL_EVENTS = text(
    """
    SELECT
        trial_index,
        event_index,
        elapsed_ms,
        event_type
    FROM iat_session_trial_events
    WHERE session_id = :session_id AND block_index = :block_index
    ORDER BY trial_index, event_index
    """
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session


class SessionRepository:
    """Persist and read session-root runtime state with direct SQL."""

    def __init__(self, database_session: Session, session_key_factory: Callable[[], str]) -> None:
        """Initialize one direct-SQL session repository.

        Args:
            database_session: Open database session used for reads and writes.
            session_key_factory: Callable used to generate public session keys.
        """
        self._database_session = database_session
        self._session_key_factory = session_key_factory

    def create_session(
        self,
        iat_slug: str,
        plan_seed: int,
        client_context: ClientContext,
    ) -> SessionState:
        """Persist one new running session root row.

        Args:
            iat_slug: Published IAT slug associated with the session.
            plan_seed: Random seed used to generate the run plan.
            client_context: Client metadata captured at session creation.

        Returns:
            The newly persisted session state.
        """
        created_at_utc = datetime.now(tz=UTC)
        for _ in range(SESSION_KEY_COLLISION_RETRY_COUNT):
            session_key = self._session_key_factory()
            savepoint = self._database_session.begin_nested()
            try:
                session_id = self._database_session.execute(
                    _INSERT_SESSION,
                    {
                        "session_key": session_key,
                        "iat_slug": iat_slug,
                        "plan_seed": plan_seed,
                        "created_at_utc": created_at_utc,
                        "user_agent": client_context.user_agent,
                        "platform": client_context.platform,
                        "viewport_width_px": client_context.viewport_width_px,
                        "viewport_height_px": client_context.viewport_height_px,
                        "device_pixel_ratio": client_context.device_pixel_ratio,
                    },
                ).scalar_one()
            except IntegrityError:
                savepoint.rollback()
                continue

            savepoint.commit()
            break
        else:
            raise SessionConfigurationError(
                "The session could not be created because a unique session key was unavailable."
            )

        return SessionState(
            session_id=session_id,
            session_key=session_key,
            created_at_utc=created_at_utc,
            completed_at_utc=None,
        )

    def save_completed_block(
        self,
        session_key: str,
        block_index: int,
        completed_block_input: CompletedBlockInput,
    ) -> None:
        """Validate and persist one completed block upload.

        Args:
            session_key: Opaque public session key.
            block_index: One-based deterministic block index to upload.
            completed_block_input: Typed raw participant payload for that completed block.
        """
        session_row = (
            self._database_session.execute(
                _SELECT_UPLOAD_CONTEXT_BY_KEY,
                {"session_key": session_key},
            )
            .mappings()
            .one_or_none()
        )
        if session_row is None:
            raise SessionNotFoundError(f"IAT session not found: {session_key}")

        session_id = session_row["id"]

        block_upload_facts = (
            self._database_session.execute(
                _SELECT_BLOCK_UPLOAD_FACTS,
                {"session_id": session_id, "block_index": block_index},
            )
            .mappings()
            .one()
        )
        expected_trial_count = block_upload_facts["trial_count"]
        if expected_trial_count < 1:
            raise SessionInputError("Block indexes must reference one configured run-plan block.")

        if session_row["completed_at_utc"] is None and block_index > block_upload_facts["uploaded_block_count"] + 1:
            raise SessionConflictError(INVALID_SESSION_STATE_MESSAGE)

        if len(completed_block_input.trials) != expected_trial_count:
            raise SessionInputError("Uploaded blocks must include the full deterministic block payload.")

        trial_event_rows: list[dict[str, int | str]] = []
        for trial_index, completed_trial_input in enumerate(completed_block_input.trials, start=1):
            if not completed_trial_input.events:
                raise SessionInputError("Uploaded trials must include at least one event.")

            last_elapsed_ms = -1
            for event_index, trial_event_input in enumerate(completed_trial_input.events, start=1):
                elapsed_ms = trial_event_input.elapsed_ms
                event_type = trial_event_input.event_type
                if elapsed_ms < last_elapsed_ms:
                    raise SessionInputError("Uploaded trial events must keep non-decreasing elapsed times.")

                last_elapsed_ms = elapsed_ms
                trial_event_rows.append(
                    {
                        "session_id": session_id,
                        "block_index": block_index,
                        "trial_index": trial_index,
                        "event_index": event_index,
                        "elapsed_ms": elapsed_ms,
                        "event_type": event_type.value,
                    }
                )

        completes_session = not block_upload_facts["has_later_blocks"]
        savepoint = self._database_session.begin_nested()

        try:
            self._database_session.execute(
                _INSERT_TRIAL_EVENT,
                trial_event_rows,
            )
            if completes_session:
                self._database_session.execute(
                    _MARK_SESSION_COMPLETED,
                    {
                        "session_id": session_id,
                        "completed_at_utc": datetime.now(tz=UTC),
                    },
                )
            savepoint.commit()
        except IntegrityError as exc:
            savepoint.rollback()
            persisted_trial_event_rows = tuple(
                (
                    persisted_event_row["trial_index"],
                    persisted_event_row["event_index"],
                    persisted_event_row["elapsed_ms"],
                    persisted_event_row["event_type"],
                )
                for persisted_event_row in self._database_session.execute(
                    _SELECT_BLOCK_TRIAL_EVENTS,
                    {"session_id": session_id, "block_index": block_index},
                ).mappings()
            )
            if persisted_trial_event_rows == tuple(
                (
                    trial_event_row["trial_index"],
                    trial_event_row["event_index"],
                    trial_event_row["elapsed_ms"],
                    trial_event_row["event_type"],
                )
                for trial_event_row in trial_event_rows
            ):
                return

            raise SessionConflictError(INVALID_SESSION_STATE_MESSAGE) from exc
