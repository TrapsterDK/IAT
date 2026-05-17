"""Tests for backend session service orchestration."""

from __future__ import annotations

import pytest

from apps.backend.domain.iat.models import PublishedCategory, PublishedIat, PublishedStimulus
from apps.backend.domain.session.exceptions import IatNotFoundError, SessionNotFoundError
from apps.backend.domain.session.models import (
    BlockUpload,
    BlockUploadInput,
    ClientContext,
    RunPlan,
    SessionState,
    SessionUploadState,
    TrialEvent,
    TrialEventType,
    TrialEventUploadInput,
    TrialUploadInput,
)
from apps.backend.repositories.iat import IatRepository
from apps.backend.repositories.session.repository import SessionRepository
from apps.backend.services.session import SessionService


class _StubIatRepository(IatRepository):
    def __init__(self, published_iat: PublishedIat | None) -> None:
        self._published_iat = published_iat

    def get_iat(self, slug: str) -> PublishedIat | None:
        return self._published_iat


class _RecordingSessionRepository(SessionRepository):
    def __init__(
        self,
        upload_state: SessionUploadState | None = None,
        created_state: SessionState | None = None,
    ) -> None:
        self._upload_state = upload_state
        self._created_state = created_state
        self.committed_block_upload: BlockUpload | None = None

    def create_execution(
        self,
        iat_slug: str,
        plan_seed: int,
        run_plan: RunPlan,
        client_context: ClientContext,
    ) -> SessionState:
        assert self._created_state is not None
        return self._created_state

    def get_upload_state_by_key(self, session_key: str) -> SessionUploadState | None:
        return self._upload_state

    def commit_block_upload(self, block_upload: BlockUpload) -> None:
        self.committed_block_upload = block_upload


def _build_published_iat() -> PublishedIat:
    return PublishedIat(
        slug="sample-iat",
        title="Sample IAT",
        description="Measures one sample association.",
        categories=(
            (
                PublishedCategory(slug="alpha", label="Alpha", stimuli=(PublishedStimulus(text="alpha"),)),
                PublishedCategory(slug="beta", label="Beta", stimuli=(PublishedStimulus(text="beta"),)),
            ),
            (
                PublishedCategory(slug="gamma", label="Gamma", stimuli=(PublishedStimulus(text="gamma"),)),
                PublishedCategory(slug="delta", label="Delta", stimuli=(PublishedStimulus(text="delta"),)),
            ),
        ),
    )


def test_create_session_raises_not_found_for_missing_iat() -> None:
    # Given: one session service whose IAT repository cannot resolve the requested slug.
    session_service = SessionService(
        iat_repository=_StubIatRepository(None),
        session_repository=_RecordingSessionRepository(),
        plan_seed_provider=lambda: 123,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
    )

    # When: one client starts one session for one missing IAT.
    # Then: the service reports the missing IAT before attempting to build or persist a run plan.
    with pytest.raises(IatNotFoundError, match="IAT not found: missing-iat"):
        session_service.create_session("missing-iat", ClientContext())


def test_upload_block_raises_not_found_for_missing_session() -> None:
    # Given: one session service whose session repository cannot resolve the requested session key.
    session_repository = _RecordingSessionRepository(upload_state=None)
    session_service = SessionService(
        iat_repository=_StubIatRepository(None),
        session_repository=session_repository,
        plan_seed_provider=lambda: 123,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
    )

    # Given: one typed block-upload input.
    block_upload_input = BlockUploadInput(
        trials=(TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: one client uploads one block for one missing session.
    # Then: the service reports the missing session before attempting to commit one upload.
    with pytest.raises(SessionNotFoundError, match="IAT session not found: missing-session"):
        session_service.upload_block("missing-session", 1, block_upload_input)


def test_upload_block_commits_validated_block_upload() -> None:
    # Given: one session service with one running session waiting for its first block.
    published_iat = _build_published_iat()
    session_repository = _RecordingSessionRepository(
        upload_state=SessionUploadState(
            session_id=7,
            completed_at_utc=None,
            block_trial_counts=(1,),
            next_trial_id=1,
            next_block_index=1,
            next_event_index=1,
            anticipation_threshold_ms=300,
            response_timeout_ms=10_000,
        )
    )
    session_service = SessionService(
        iat_repository=_StubIatRepository(published_iat),
        session_repository=session_repository,
        plan_seed_provider=lambda: 123,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
    )
    block_upload_input = BlockUploadInput(
        trials=(TrialUploadInput(events=(TrialEventUploadInput(event_type=TrialEventType.LEFT, elapsed_ms=350),)),)
    )

    # When: the client uploads one valid deterministic block.
    session_service.upload_block("session-key", 1, block_upload_input)

    # Then: the service commits the validated canonical block upload to the repository.
    assert session_repository.committed_block_upload == BlockUpload(
        session_id=7,
        trial_events=(TrialEvent(trial_id=1, event_index=1, elapsed_ms=350, event_type=TrialEventType.LEFT),),
        completes_session=True,
    )
