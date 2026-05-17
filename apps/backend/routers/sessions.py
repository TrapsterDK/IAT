"""FastAPI routes for participant-facing IAT session runtime flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response

from apps.backend.dependencies import get_session_service
from apps.backend.domain.session.exceptions import (
    IatNotFoundError,
    SessionConfigurationError,
    SessionConflictError,
    SessionInputError,
    SessionNotFoundError,
)
from apps.backend.domain.session.models import (
    BlockUploadInput,
    ClientContext,
    TrialEventUploadInput,
    TrialUploadInput,
)
from apps.backend.models.session import (
    ClientContextRequest,
    CreateSessionRequest,
    RunPlanBlockResponse,
    RunPlanTrialResponse,
    SessionBootstrapResponse,
    SessionStimulusResponse,
    UploadBlockRequest,
)
from apps.backend.routers.stimuli import build_stimulus_url
from apps.backend.services.session import SessionService  # noqa: TC001

if TYPE_CHECKING:
    from apps.backend.domain.session.models import BlockPlan, RunPlan, SessionState

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
        state, run_plan = session_service.create_session(
            create_request.iat_slug,
            client_context=_build_client_context(create_request.client_context),
        )
    except IatNotFoundError as exc:
        raise HTTPException(status_code=404, detail="IAT not found.") from exc
    except SessionConfigurationError as exc:
        raise HTTPException(status_code=500, detail="IAT configuration is invalid.") from exc

    return _build_session_bootstrap_response(state, run_plan, request)


@router.put("/{session_key}/blocks/{block_index}", status_code=204)
def upload_block(
    session_key: str,
    block_index: Annotated[int, Path(ge=1)],
    upload_request: UploadBlockRequest,
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
        session_service.upload_block(
            session_key,
            block_index,
            _build_block_upload_input(upload_request),
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


def _build_client_context(client_context_request: ClientContextRequest | None) -> ClientContext:
    if client_context_request is None:
        return ClientContext()
    return ClientContext(
        user_agent=client_context_request.user_agent,
        platform=client_context_request.platform,
        viewport_width_px=client_context_request.viewport_width_px,
        viewport_height_px=client_context_request.viewport_height_px,
        device_pixel_ratio=client_context_request.device_pixel_ratio,
    )


def _build_block_upload_input(upload_request: UploadBlockRequest) -> BlockUploadInput:
    return BlockUploadInput(
        trials=tuple(
            TrialUploadInput(
                events=tuple(
                    TrialEventUploadInput(
                        event_type=uploaded_event.event_type,
                        elapsed_ms=uploaded_event.elapsed_ms,
                    )
                    for uploaded_event in uploaded_trial.events
                )
            )
            for uploaded_trial in upload_request.trials
        )
    )


def _build_session_bootstrap_response(
    state: SessionState,
    run_plan: RunPlan,
    request: Request,
) -> SessionBootstrapResponse:
    return SessionBootstrapResponse(
        session_key=state.session_key,
        anticipation_threshold_ms=run_plan.anticipation_threshold_ms,
        response_timeout_ms=run_plan.response_timeout_ms,
        blocks=tuple(_build_block_response(block, request) for block in run_plan.blocks),
    )


def _build_block_response(block: BlockPlan, request: Request) -> RunPlanBlockResponse:
    return RunPlanBlockResponse(
        left_labels=block.left_labels,
        right_labels=block.right_labels,
        is_practice=block.is_practice,
        trials=tuple(
            RunPlanTrialResponse(
                stimulus=SessionStimulusResponse(
                    text=trial.stimulus.text,
                    image_url=(
                        None
                        if trial.stimulus.image_path is None
                        else build_stimulus_url(request, trial.stimulus.image_path)
                    ),
                ),
                correct_response_side=trial.correct_response_side,
            )
            for trial in block.trials
        ),
    )
