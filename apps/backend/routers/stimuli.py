"""FastAPI routes for public image stimuli."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from apps.backend.dependencies import get_iat_service
from apps.backend.services.iat import IatService  # noqa: TC001

router = APIRouter(prefix="/stimuli", tags=["stimuli"])


@router.get("/{stimulus_path:path}")
def get_stimulus(
    stimulus_path: str,
    iat_service: Annotated[IatService, Depends(get_iat_service)],
) -> FileResponse:
    """Serve one public PNG stimulus.

    Args:
        stimulus_path: Public path below the configured stimuli root.
        iat_service: Shared backend IAT service.

    Returns:
        The requested PNG file response.

    Raises:
        HTTPException: The requested path is invalid or unavailable.
    """
    resolved_path = iat_service.get_stimulus(PurePosixPath(stimulus_path))
    if resolved_path is None:
        raise HTTPException(status_code=404, detail="Stimulus not found.")

    return FileResponse(resolved_path, media_type="image/png")
