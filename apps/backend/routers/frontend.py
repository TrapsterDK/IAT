"""Frontend routes for the participant-facing single-page app shell."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from apps.backend.dependencies import get_frontend_dist_directory

router = APIRouter(tags=["frontend"])


@router.get("/", include_in_schema=False)
def get_index(dist_directory: Annotated[Path, Depends(get_frontend_dist_directory)]) -> FileResponse:
    """Serve the participant-facing frontend HTML shell.

    Args:
        dist_directory: The configured built frontend `dist/` directory.

    Returns:
        The built frontend `index.html` response.
    """
    index_path = dist_directory / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="IAT website is not available.")

    return FileResponse(index_path, media_type="text/html; charset=utf-8")


@router.get("/assets/{asset_path:path}", include_in_schema=False)
def get_asset(asset_path: str, dist_directory: Annotated[Path, Depends(get_frontend_dist_directory)]) -> FileResponse:
    """Serve one built frontend asset.

    Args:
        asset_path: Asset path relative to the built frontend `assets/` directory.
        dist_directory: The configured built frontend `dist/` directory.

    Returns:
        The built asset response.
    """
    asset_path_resolved = dist_directory / "assets" / asset_path
    if not asset_path_resolved.is_file():
        raise HTTPException(status_code=404, detail="Requested asset is not available.")

    return FileResponse(asset_path_resolved)
