"""Application service for participant-facing IAT session runtime flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.backend.domain.session.exceptions import (
    IatNotFoundError,
    SessionNotFoundError,
)
from apps.backend.domain.session.run_plan_builder import build_run_plan
from apps.backend.domain.session.scoring import calculate_session_score

if TYPE_CHECKING:
    from collections.abc import Callable

    from apps.backend.models.plan import RunPlan
    from apps.backend.models.scoring import SessionScoreResult
    from apps.backend.models.session import CompletedBlockInput, SessionCreateInput, SessionState
    from apps.backend.repositories.catalog import CatalogRepository
    from apps.backend.repositories.session.plan import SessionPlanRepository
    from apps.backend.repositories.session.scoring import SessionScoringRepository
    from apps.backend.repositories.session.session import SessionRepository
    from apps.backend.settings import SessionScoreInterpretationSettings


class SessionService:
    """Orchestrate participant session runtime behavior on top of repositories."""

    def __init__(
        self,
        catalog_repository: CatalogRepository,
        session_repository: SessionRepository,
        plan_repository: SessionPlanRepository,
        scoring_repository: SessionScoringRepository,
        plan_seed_provider: Callable[[], int],
        score_interpretation: SessionScoreInterpretationSettings,
    ) -> None:
        """Initialize one session runtime service.

        Args:
            catalog_repository: Published catalog repository used to load the deterministic source IAT.
            session_repository: Session repository used for persisted session state and uploads.
            plan_repository: Session-plan repository used for immutable run-plan persistence.
            scoring_repository: Session scoring repository used for completed-session scoring projections.
            plan_seed_provider: Callable used to generate deterministic run-plan seeds.
            score_interpretation: Configured D-score headline thresholds.
        """
        self._catalog_repository = catalog_repository
        self._session_repository = session_repository
        self._plan_repository = plan_repository
        self._scoring_repository = scoring_repository
        self._plan_seed_provider = plan_seed_provider
        self._score_interpretation = score_interpretation

    def create_session(self, session_create_input: SessionCreateInput) -> tuple[SessionState, RunPlan]:
        """Create and immediately start one participant session for one published IAT.

        Args:
            session_create_input: Typed session-creation payload from the API boundary.

        Returns:
            The created persisted session state and run plan.

        Raises:
            IatNotFoundError: The requested IAT does not exist.
        """
        catalog_iat = self._catalog_repository.get_iat(session_create_input.iat_slug)
        if catalog_iat is None:
            raise IatNotFoundError(f"IAT not found: {session_create_input.iat_slug}")

        plan_seed = self._plan_seed_provider()
        run_plan = build_run_plan(
            catalog_iat,
            seed=plan_seed,
        )
        state = self._session_repository.create_session(
            catalog_iat.slug,
            plan_seed,
            session_create_input.client_context,
        )
        self._plan_repository.save_plan(state.session_id, run_plan)
        return state, run_plan

    def complete_block(
        self,
        session_key: str,
        block_index: int,
        completed_block_input: CompletedBlockInput,
    ) -> None:
        """Record one completed block of participant trial results.

        Args:
            session_key: Opaque public session key.
            block_index: One-based block index in the deterministic run plan.
            completed_block_input: Typed raw domain payload for that completed block.

        Raises:
            SessionNotFoundError: The requested session does not exist.
        """
        self._session_repository.save_completed_block(session_key, block_index, completed_block_input)

    def get_score(self, session_key: str) -> SessionScoreResult:
        """Return one computed score for one completed participant session.

        Args:
            session_key: Opaque public session key.

        Returns:
            The computed session score result.

        Raises:
            SessionNotFoundError: The requested session does not exist.
            SessionConflictError: The session cannot be scored yet.
        """
        completed_session_snapshot = self._scoring_repository.get_completed_session_snapshot_by_key(session_key)
        if completed_session_snapshot is None:
            raise SessionNotFoundError(f"IAT session not found: {session_key}")

        return calculate_session_score(
            completed_session_snapshot,
            little_to_no_association_upper_bound=self._score_interpretation.little_to_no_association_upper_bound,
            slight_association_upper_bound=self._score_interpretation.slight_association_upper_bound,
            moderate_association_upper_bound=self._score_interpretation.moderate_association_upper_bound,
        )
