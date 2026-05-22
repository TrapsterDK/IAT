"""FastAPI routes for participant-facing IAT session runtime flow."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response

from apps.backend.dependencies import get_session_service
from apps.backend.domain.session.exceptions import (
    IatNotFoundError,
    SessionConfigurationError,
    SessionConflictError,
    SessionInputError,
    SessionNotFoundError,
    SessionUnscoreableError,
)
from apps.backend.routers.stimuli import build_stimulus_url
from apps.backend.schemas.session import (
    CompletedBlockRequest,
    CreateSessionRequest,
    SessionBootstrapResponse,
    SessionScoreResponse,
    StimulusUrlBuilder,
)
from apps.backend.services.session import SessionService  # noqa: TC001

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=201)
def create_session(
    request: Request,
    create_request: CreateSessionRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionBootstrapResponse:
    """Create and start one participant session for one published IAT.

    Args:
        request: Current request used to build public stimulus URLs.
        create_request: Public session-creation payload.
        session_service: Request-scoped participant session service.

    Returns:
        The created participant-facing session snapshot.

    Raises:
        HTTPException: The requested IAT does not exist.
    """
    try:
        state, run_plan = session_service.create_session(create_request.to_business())
    except IatNotFoundError as exc:
        raise HTTPException(status_code=404, detail="IAT not found.") from exc
    except SessionConfigurationError as exc:
        raise HTTPException(status_code=500, detail="IAT configuration is invalid.") from exc

    return SessionBootstrapResponse.from_business(state, run_plan, _build_stimulus_url_builder(request))


@router.put("/{session_key}/blocks/{block_index}", status_code=204)
def complete_block(
    session_key: str,
    block_index: Annotated[int, Path(ge=1)],
    upload_request: CompletedBlockRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> Response:
    """Commit one completed deterministic block upload.

    Args:
        session_key: Opaque public session key.
        block_index: One-based block index in the deterministic run plan.
        upload_request: Completed block payload from the client runtime.
        session_service: Request-scoped participant session service.

    Returns:
        One empty success response when the block is committed.

    Raises:
        HTTPException: The session is missing, conflicted, or invalid for the submitted payload.
    """
    try:
        session_service.complete_block(
            session_key,
            block_index,
            upload_request.to_business(),
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc
    except SessionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="The block upload could not be committed because the session state is invalid.",
        ) from exc
    except SessionInputError as exc:
        raise HTTPException(status_code=422, detail="The block upload payload is invalid.") from exc

    return Response(status_code=204)


@router.get("/{session_key}/score")
def get_score(
    session_key: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionScoreResponse:
    """Return one computed score for one completed participant session.

    Args:
        session_key: Opaque public session key.
        session_service: Request-scoped participant session service.

    Returns:
        The computed D-score and one user-facing headline.

    Raises:
        HTTPException: The session is missing or not scoreable yet.
    """
    try:
        session_score = session_service.get_score(session_key)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc
    except SessionUnscoreableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail="The session score is unavailable.") from exc

    return SessionScoreResponse.from_business(session_score)


def _build_stimulus_url_builder(request: Request) -> StimulusUrlBuilder:
    return lambda image_path: build_stimulus_url(request, image_path)
