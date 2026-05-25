"""Shared helpers for session repository tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.backend.database import create_database_schema, create_session_factory, create_sqlite_engine
from apps.backend.models.plan import BlockPlan, PlannedStimulus, ResponseSide, RunPlan, TrialPlan
from apps.backend.models.session import ClientContext, SessionMode, SessionState, TrialEventType
from apps.backend.repositories.session.plan import SessionPlanRepository
from apps.backend.repositories.session.schema import SessionTrialEventRecord
from apps.backend.repositories.session.scoring import SessionScoringRepository
from apps.backend.repositories.session.session import SessionRepository

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session, sessionmaker

    from apps.backend.models.scoring import CompletedSessionSnapshot


def create_execution(
    database_session: Session,
    session_key_factory: Callable[[], str],
    iat_slug: str,
    plan_seed: int,
    run_plan: RunPlan,
    client_context: ClientContext,
    session_mode: SessionMode,
) -> SessionState:
    """Create one session and persist its immutable run plan.

    Args:
        database_session: Open SQLAlchemy session used for persistence.
        session_key_factory: Factory that returns the next public session key.
        iat_slug: Published IAT slug for the created session.
        plan_seed: Seed used to create the session state.
        run_plan: Immutable run plan saved for the new session.
        client_context: Client metadata stored with the session.
        session_mode: Publicly visible mode stored for the created session.

    Returns:
        The newly created session state.
    """
    session_repository = SessionRepository(database_session, session_key_factory=session_key_factory)
    plan_repository = SessionPlanRepository(database_session)
    created_state = session_repository.create_session(
        iat_slug,
        plan_seed,
        client_context,
        session_mode,
    )
    plan_repository.save_plan(created_state.session_id, run_plan)
    return created_state


def get_completed_session_snapshot(
    database_session: Session,
    session_key: str,
) -> CompletedSessionSnapshot | None:
    """Load one completed-session snapshot by public session key.

    Args:
        database_session: Open SQLAlchemy session used for the lookup.
        session_key: Public session key for the completed session.

    Returns:
        The completed-session snapshot when one exists, otherwise ``None``.
    """
    return SessionScoringRepository(database_session).get_completed_session_snapshot_by_key(session_key)


def build_run_plan() -> RunPlan:
    """Build one compact two-block run plan for repository tests.

    Returns:
        A deterministic run plan with one practice block and one scored block.
    """
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


def build_standard_score_run_plan() -> RunPlan:
    """Build one seven-block run plan that exercises scoring behavior.

    Returns:
        A deterministic seven-block run plan that covers the scoring flow.
    """
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


def append_single_event_trials(
    database_session: Session,
    session_id: int,
    block_trial_latencies: dict[int, tuple[int, ...]],
) -> None:
    """Insert one event per trial for the provided block latencies.

    Args:
        database_session: Open SQLAlchemy session used for inserts.
        session_id: Database identifier for the session receiving trial events.
        block_trial_latencies: Mapping of block index to per-trial elapsed times.
    """
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


def build_repository_factory(tmp_path: Path) -> tuple[Engine, sessionmaker[Session]]:
    """Create one temporary SQLite-backed session factory for tests.

    Args:
        tmp_path: Temporary pytest directory used for the SQLite database file.

    Returns:
        The SQLite engine and a session factory bound to that engine.
    """
    engine = create_sqlite_engine(tmp_path / "instance/session-repository.sqlite3")
    create_database_schema(engine)
    return engine, create_session_factory(engine)
