"""Application service for participant-facing IAT session runtime flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.backend.domain.session.exceptions import (
    IatNotFoundError,
    SessionNotFoundError,
)
from apps.backend.domain.session.execution import build_block_upload
from apps.backend.domain.session.run_plan_builder import build_run_plan

if TYPE_CHECKING:
    from collections.abc import Callable

    from apps.backend.domain.session.models import BlockUploadInput, ClientContext, RunPlan, SessionState
    from apps.backend.repositories.iat import IatRepository
    from apps.backend.repositories.session.repository import SessionRepository


class SessionService:
    """Orchestrate participant session runtime behavior on top of repositories."""

    def __init__(
        self,
        iat_repository: IatRepository,
        session_repository: SessionRepository,
        plan_seed_provider: Callable[[], int],
        anticipation_threshold_ms: int,
        response_timeout_ms: int,
    ) -> None:
        """Initialize one session runtime service.

        Args:
            iat_repository: Published IAT repository used to load the deterministic source IAT.
            session_repository: Session persistence repository.
            plan_seed_provider: Callable used to generate deterministic run-plan seeds.
            anticipation_threshold_ms: Configured anticipation threshold for new run plans.
            response_timeout_ms: Configured response timeout for new run plans.
        """
        self._iat_repository = iat_repository
        self._session_repository = session_repository
        self._plan_seed_provider = plan_seed_provider
        self._anticipation_threshold_ms = anticipation_threshold_ms
        self._response_timeout_ms = response_timeout_ms

    def create_session(self, iat_slug: str, client_context: ClientContext) -> tuple[SessionState, RunPlan]:
        """Create and immediately start one participant session for one published IAT.

        Args:
            iat_slug: Requested published IAT slug.
            client_context: Client metadata captured at session start.

        Returns:
            The created persisted session state and run plan.

        Raises:
            IatNotFoundError: The requested IAT does not exist.
        """
        published_iat = self._iat_repository.get_iat(iat_slug)
        if published_iat is None:
            raise IatNotFoundError(f"IAT not found: {iat_slug}")

        plan_seed = self._plan_seed_provider()
        run_plan = build_run_plan(
            published_iat,
            anticipation_threshold_ms=self._anticipation_threshold_ms,
            response_timeout_ms=self._response_timeout_ms,
            seed=plan_seed,
        )
        state = self._session_repository.create_execution(published_iat.slug, plan_seed, run_plan, client_context)
        return state, run_plan

    def upload_block(
        self,
        session_key: str,
        block_index: int,
        block_upload_input: BlockUploadInput,
    ) -> None:
        """Record one completed block of participant trial results.

        Args:
            session_key: Opaque public session key.
            block_index: One-based block index in the deterministic run plan.
            block_upload_input: Typed raw domain upload payload for that block.

        Raises:
            SessionNotFoundError: The requested session does not exist.
        """
        session_upload_state = self._session_repository.get_upload_state_by_key(session_key)
        if session_upload_state is None:
            raise SessionNotFoundError(f"IAT session not found: {session_key}")

        block_upload = build_block_upload(session_upload_state, block_index, block_upload_input)
        self._session_repository.commit_block_upload(block_upload)
