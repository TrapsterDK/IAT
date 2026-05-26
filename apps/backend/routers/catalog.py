"""FastAPI routes for the published IAT catalog."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.backend.dependencies import get_catalog_service
from apps.backend.routers.stimuli import build_stimulus_url
from apps.backend.schemas.catalog import IatResponse, IatSummaryResponse, StimulusUrlBuilder
from apps.backend.services.catalog import CatalogService  # noqa: TC001
from libs.pydantic.types import Slug  # noqa: TC001

router = APIRouter(prefix="/iats", tags=["catalog"])


@router.get("")
def list_iats(catalog_service: Annotated[CatalogService, Depends(get_catalog_service)]) -> list[IatSummaryResponse]:
    """List the currently available published IATs.

    Args:
        catalog_service: Shared backend catalog service.

    Returns:
        The available IAT summaries.
    """
    return [IatSummaryResponse.from_business(iat_summary) for iat_summary in catalog_service.get_iats()]


@router.get("/{slug}")
def get_iat(
    slug: Slug,
    request: Request,
    catalog_service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> IatResponse:
    """Return one published IAT definition by slug.

    Args:
        slug: Requested IAT slug.
        request: Current request used to build public stimulus URLs.
        catalog_service: Shared backend catalog service.

    Returns:
        The resolved IAT response.

    Raises:
        HTTPException: The requested IAT does not exist.
    """
    published_iat = catalog_service.get_iat(slug)
    if published_iat is None:
        raise HTTPException(status_code=404, detail="IAT not found.")

    return IatResponse.from_business(published_iat, _build_stimulus_url_builder(request))


def _build_stimulus_url_builder(request: Request) -> StimulusUrlBuilder:
    return lambda image_path: build_stimulus_url(request, image_path)
