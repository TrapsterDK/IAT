"""Tests for backend session service orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from apps.backend.domain.session.exceptions import IatNotFoundError, SessionNotFoundError
from apps.backend.models.catalog import CatalogCategory, CatalogIat, CatalogStimulus
from apps.backend.models.plan import ResponseSide
from apps.backend.models.scoring import (
    CompletedSessionSnapshot,
    SessionScoringBlock,
    SessionScoringEvent,
    SessionScoringTrial,
)
from apps.backend.models.session import (
    ClientContext,
    CompletedBlockInput,
    CompletedTrialInput,
    SessionCreateInput,
    SessionState,
    TrialEventInput,
    TrialEventType,
)
from apps.backend.repositories.catalog import CatalogRepository
from apps.backend.repositories.session.plan import SessionPlanRepository
from apps.backend.repositories.session.scoring import SessionScoringRepository
from apps.backend.repositories.session.session import SessionRepository
from apps.backend.services.session import SessionService
from apps.backend.settings import SessionScoreInterpretationSettings

if TYPE_CHECKING:
    from apps.backend.models.plan import RunPlan


class _StubCatalogRepository(CatalogRepository):
    def __init__(self, catalog_iat: CatalogIat | None) -> None:
        self._catalog_iat = catalog_iat

    def get_iat(self, slug: str) -> CatalogIat | None:
        return self._catalog_iat


class _RecordingSessionRepository(SessionRepository):
    def __init__(
        self,
        missing_session_key: str | None = None,
        created_state: SessionState | None = None,
    ) -> None:
        self._missing_session_key = missing_session_key
        self._created_state = created_state
        self.saved_completed_block_call: tuple[str, int, CompletedBlockInput] | None = None

    def create_session(
        self,
        iat_slug: str,
        plan_seed: int,
        client_context: ClientContext,
    ) -> SessionState:
        assert self._created_state is not None
        return self._created_state

    def save_completed_block(
        self, session_key: str, block_index: int, completed_block_input: CompletedBlockInput
    ) -> None:
        if session_key == self._missing_session_key:
            raise SessionNotFoundError(f"IAT session not found: {session_key}")

        self.saved_completed_block_call = (session_key, block_index, completed_block_input)


class _RecordingSessionPlanRepository(SessionPlanRepository):
    def __init__(self) -> None:
        self.persisted_plan: tuple[int, RunPlan] | None = None

    def save_plan(self, session_id: int, run_plan: RunPlan) -> None:
        self.persisted_plan = (session_id, run_plan)


class _StubSessionScoringRepository(SessionScoringRepository):
    def __init__(self, scoring_data: CompletedSessionSnapshot | None = None) -> None:
        self._scoring_data = scoring_data

    def get_completed_session_snapshot_by_key(self, session_key: str) -> CompletedSessionSnapshot | None:
        return self._scoring_data


def _build_catalog_iat() -> CatalogIat:
    return CatalogIat(
        slug="sample-iat",
        title="Sample IAT",
        description="Measures one sample association.",
        categories=(
            (
                CatalogCategory(slug="alpha", label="Alpha", stimuli=(CatalogStimulus(text="alpha"),)),
                CatalogCategory(slug="beta", label="Beta", stimuli=(CatalogStimulus(text="beta"),)),
            ),
            (
                CatalogCategory(slug="gamma", label="Gamma", stimuli=(CatalogStimulus(text="gamma"),)),
                CatalogCategory(slug="delta", label="Delta", stimuli=(CatalogStimulus(text="delta"),)),
            ),
        ),
    )


def _build_score_thresholds() -> SessionScoreInterpretationSettings:
    return SessionScoreInterpretationSettings(
        little_to_no_association_upper_bound=0.15,
        slight_association_upper_bound=0.35,
        moderate_association_upper_bound=0.65,
    )


def _build_completed_scoring_data() -> CompletedSessionSnapshot:
    return CompletedSessionSnapshot(
        blocks=(
            SessionScoringBlock(
                left_labels=("Alpha",),
                right_labels=("Beta",),
                is_practice=True,
                trials=(),
            ),
            SessionScoringBlock(
                left_labels=("Gamma",),
                right_labels=("Delta",),
                is_practice=True,
                trials=(),
            ),
            SessionScoringBlock(
                left_labels=("Alpha", "Gamma"),
                right_labels=("Beta", "Delta"),
                is_practice=True,
                trials=(
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.LEFT,
                        events=(SessionScoringEvent(event_type=TrialEventType.LEFT, elapsed_ms=400),),
                    ),
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.RIGHT,
                        events=(SessionScoringEvent(event_type=TrialEventType.RIGHT, elapsed_ms=400),),
                    ),
                ),
            ),
            SessionScoringBlock(
                left_labels=("Alpha", "Gamma"),
                right_labels=("Beta", "Delta"),
                is_practice=False,
                trials=(
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.LEFT,
                        events=(SessionScoringEvent(event_type=TrialEventType.LEFT, elapsed_ms=410),),
                    ),
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.RIGHT,
                        events=(SessionScoringEvent(event_type=TrialEventType.RIGHT, elapsed_ms=410),),
                    ),
                ),
            ),
            SessionScoringBlock(
                left_labels=("Beta",),
                right_labels=("Alpha",),
                is_practice=True,
                trials=(),
            ),
            SessionScoringBlock(
                left_labels=("Beta", "Gamma"),
                right_labels=("Alpha", "Delta"),
                is_practice=True,
                trials=(
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.LEFT,
                        events=(SessionScoringEvent(event_type=TrialEventType.LEFT, elapsed_ms=700),),
                    ),
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.RIGHT,
                        events=(SessionScoringEvent(event_type=TrialEventType.RIGHT, elapsed_ms=700),),
                    ),
                ),
            ),
            SessionScoringBlock(
                left_labels=("Beta", "Gamma"),
                right_labels=("Alpha", "Delta"),
                is_practice=False,
                trials=(
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.LEFT,
                        events=(SessionScoringEvent(event_type=TrialEventType.LEFT, elapsed_ms=710),),
                    ),
                    SessionScoringTrial(
                        correct_response_side=ResponseSide.RIGHT,
                        events=(SessionScoringEvent(event_type=TrialEventType.RIGHT, elapsed_ms=710),),
                    ),
                ),
            ),
        ),
    )


def test_create_session_raises_not_found_for_missing_iat() -> None:
    # Given: one session service whose IAT repository cannot resolve the requested slug.
    session_service = SessionService(
        catalog_repository=_StubCatalogRepository(None),
        session_repository=_RecordingSessionRepository(),
        plan_repository=_RecordingSessionPlanRepository(),
        scoring_repository=_StubSessionScoringRepository(),
        plan_seed_provider=lambda: 123,
        score_interpretation=_build_score_thresholds(),
    )

    # When: one client starts one session for one missing IAT.
    # Then: the service reports the missing IAT before attempting to build or persist a run plan.
    with pytest.raises(IatNotFoundError, match="IAT not found: missing-iat"):
        session_service.create_session(SessionCreateInput(iat_slug="missing-iat", client_context=ClientContext()))


def test_complete_block_raises_not_found_for_missing_session() -> None:
    # Given: one session service whose session repository cannot resolve the requested session key.
    session_repository = _RecordingSessionRepository(missing_session_key="missing-session")
    session_service = SessionService(
        catalog_repository=_StubCatalogRepository(None),
        session_repository=session_repository,
        plan_repository=_RecordingSessionPlanRepository(),
        scoring_repository=_StubSessionScoringRepository(),
        plan_seed_provider=lambda: 123,
        score_interpretation=_build_score_thresholds(),
    )

    # Given: one typed block-upload input.
    completed_block_input = CompletedBlockInput(
        trials=(CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: one client uploads one block for one missing session.
    # Then: the service reports the missing session before attempting to commit one upload.
    with pytest.raises(SessionNotFoundError, match="IAT session not found: missing-session"):
        session_service.complete_block("missing-session", 1, completed_block_input)


def test_complete_block_saves_validated_completed_block() -> None:
    # Given: one session service with one repository ready to save one upload command.
    catalog_iat = _build_catalog_iat()
    session_repository = _RecordingSessionRepository()
    session_service = SessionService(
        catalog_repository=_StubCatalogRepository(catalog_iat),
        session_repository=session_repository,
        plan_repository=_RecordingSessionPlanRepository(),
        scoring_repository=_StubSessionScoringRepository(),
        plan_seed_provider=lambda: 123,
        score_interpretation=_build_score_thresholds(),
    )
    completed_block_input = CompletedBlockInput(
        trials=(CompletedTrialInput(events=(TrialEventInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: the client uploads one valid deterministic block.
    session_service.complete_block("session-key", 1, completed_block_input)

    # Then: the service delegates the upload command directly to the repository.
    assert session_repository.saved_completed_block_call == ("session-key", 1, completed_block_input)


def test_get_score_raises_not_found_for_missing_session() -> None:
    # Given: one session service whose repository cannot resolve the requested completed session.
    session_service = SessionService(
        catalog_repository=_StubCatalogRepository(None),
        session_repository=_RecordingSessionRepository(),
        plan_repository=_RecordingSessionPlanRepository(),
        scoring_repository=_StubSessionScoringRepository(scoring_data=None),
        plan_seed_provider=lambda: 123,
        score_interpretation=_build_score_thresholds(),
    )

    # When: one client requests one score for one missing session.
    # Then: the service reports the missing session.
    with pytest.raises(SessionNotFoundError, match="IAT session not found: missing-session"):
        session_service.get_score("missing-session")


def test_get_score_returns_computed_score_for_completed_session() -> None:
    # Given: one session service whose repository returns one completed scoring aggregate.
    session_service = SessionService(
        catalog_repository=_StubCatalogRepository(None),
        session_repository=_RecordingSessionRepository(),
        plan_repository=_RecordingSessionPlanRepository(),
        scoring_repository=_StubSessionScoringRepository(scoring_data=_build_completed_scoring_data()),
        plan_seed_provider=lambda: 123,
        score_interpretation=_build_score_thresholds(),
    )

    # When: one client requests one score for that completed session.
    score_result = session_service.get_score("session-key")

    # Then: the service returns the computed D-score and public headline.
    assert score_result.d_score > 0.65
    assert score_result.headline == "Strong automatic association of Alpha with Gamma."
