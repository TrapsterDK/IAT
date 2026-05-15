"""FastAPI routes for IAT metadata and definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.backend.dependencies import get_iat_service
from apps.backend.models import (
    CategoryPairResponse,
    CategoryResponse,
    IatResponse,
    IatSummaryResponse,
    StimulusResponse,
)
from apps.backend.services.iat import IatService  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import PurePosixPath

    from apps.backend.repositories.iat import (
        PublishedCategory,
        PublishedCategoryPair,
        PublishedIat,
        PublishedStimulus,
    )

router = APIRouter(prefix="/iats", tags=["iats"])


@router.get("")
def list_iats(iat_service: Annotated[IatService, Depends(get_iat_service)]) -> list[IatSummaryResponse]:
    """List the currently available IATs.

    Args:
        iat_service: Shared backend IAT service.

    Returns:
        The available IAT summaries.
    """
    return [_build_iat_summary_response(iat_summary) for iat_summary in iat_service.get_iats()]


@router.get("/{slug}")
def get_iat(
    slug: str,
    request: Request,
    iat_service: Annotated[IatService, Depends(get_iat_service)],
) -> IatResponse:
    """Return one IAT definition by slug.

    Args:
        slug: Requested IAT slug.
        request: Current request used to build public stimulus URLs.
        iat_service: Shared backend IAT service.

    Returns:
        The resolved IAT response.

    Raises:
        HTTPException: The requested IAT does not exist.
    """
    published_iat = iat_service.get_iat(slug)
    if published_iat is None:
        raise HTTPException(status_code=404, detail="IAT not found.")

    return _build_iat_response(published_iat, request)


def _build_iat_summary_response(iat_summary: PublishedIat) -> IatSummaryResponse:
    return IatSummaryResponse(
        slug=iat_summary.slug,
        title=iat_summary.title,
        description=iat_summary.description,
    )


def _build_iat_response(iat: PublishedIat, request: Request) -> IatResponse:
    first_pair, second_pair = iat.categories
    return IatResponse(
        slug=iat.slug,
        title=iat.title,
        description=iat.description,
        categories=(
            _build_category_pair(first_pair, request),
            _build_category_pair(second_pair, request),
        ),
    )


def _build_category_pair(pair: PublishedCategoryPair, request: Request) -> CategoryPairResponse:
    first_category, second_category = pair
    return CategoryPairResponse(
        category=(
            _build_category(first_category, request),
            _build_category(second_category, request),
        )
    )


def _build_category(category: PublishedCategory, request: Request) -> CategoryResponse:
    return CategoryResponse(
        slug=category.slug,
        label=category.label,
        stimuli=[_build_stimulus(stimulus, request) for stimulus in category.stimuli],
    )


def _build_stimulus(stimulus: PublishedStimulus, request: Request) -> StimulusResponse:
    if stimulus.text is not None:
        return StimulusResponse(text=stimulus.text)

    if stimulus.image is None:
        raise ValueError("Published image stimuli must define one public image path.")

    return StimulusResponse(image_url=_build_stimulus_url(request, stimulus.image))


def _build_stimulus_url(request: Request, image: PurePosixPath) -> str:
    return str(request.url_for("get_stimulus", stimulus_path=image.as_posix()).path)
