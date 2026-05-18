"""Public API response schemas for published catalog IAT data."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from libs.pydantic.types import NonBlankString  # noqa: TC001

if TYPE_CHECKING:
    from apps.backend.models.catalog import (
        CatalogCategory,
        CatalogCategoryPair,
        CatalogIat,
        CatalogStimulus,
    )

type StimulusUrlBuilder = Callable[[PurePosixPath], str]


class StimulusResponse(BaseModel):
    """One public text or image stimulus returned by the backend."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: NonBlankString | None = None
    image_url: NonBlankString | None = None

    @model_validator(mode="after")
    def validate_stimulus(self) -> Self:
        """Require exactly one public stimulus representation.

        Returns:
            The validated public stimulus instance.
        """
        if (self.text is None) == (self.image_url is None):
            raise ValueError("Each stimulus must define exactly one of 'text' or 'image_url'.")

        return self

    @classmethod
    def from_business(cls, stimulus: CatalogStimulus, build_image_url: StimulusUrlBuilder) -> StimulusResponse:
        """Build one public response from one published stimulus.

        Args:
            stimulus: Published stimulus to expose through the API.
            build_image_url: Builder for public image URLs.

        Returns:
            The public stimulus response.
        """
        if stimulus.image_path is not None:
            return cls(image_url=build_image_url(stimulus.image_path))

        return cls(text=stimulus.text)


class CategoryResponse(BaseModel):
    """One labeled category in one public IAT response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: NonBlankString
    label: NonBlankString
    stimuli: list[StimulusResponse] = Field(min_length=1)

    @classmethod
    def from_business(cls, category: CatalogCategory, build_image_url: StimulusUrlBuilder) -> CategoryResponse:
        """Build one public response from one published category.

        Args:
            category: Published category to expose through the API.
            build_image_url: Builder for public image URLs.

        Returns:
            The public category response.
        """
        return cls(
            slug=category.slug,
            label=category.label,
            stimuli=[StimulusResponse.from_business(stimulus, build_image_url) for stimulus in category.stimuli],
        )


class CategoryPairResponse(BaseModel):
    """One two-category block in one public IAT response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: tuple[CategoryResponse, CategoryResponse]

    @classmethod
    def from_business(cls, pair: CatalogCategoryPair, build_image_url: StimulusUrlBuilder) -> CategoryPairResponse:
        """Build one public response from one published category pair.

        Args:
            pair: Published category pair to expose through the API.
            build_image_url: Builder for public image URLs.

        Returns:
            The public category-pair response.
        """
        first_category, second_category = pair
        return cls(
            category=(
                CategoryResponse.from_business(first_category, build_image_url),
                CategoryResponse.from_business(second_category, build_image_url),
            )
        )


class IatSummaryResponse(BaseModel):
    """Summary metadata for one IAT."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: NonBlankString
    title: NonBlankString
    description: NonBlankString

    @classmethod
    def from_business(cls, iat: CatalogIat) -> IatSummaryResponse:
        """Build one public summary response from one published IAT.

        Args:
            iat: Published IAT to expose through the API.

        Returns:
            The public IAT summary response.
        """
        return cls(slug=iat.slug, title=iat.title, description=iat.description)


class IatResponse(BaseModel):
    """Public response payload for one fully resolved IAT."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: NonBlankString
    title: NonBlankString
    description: NonBlankString
    categories: tuple[CategoryPairResponse, CategoryPairResponse]

    @classmethod
    def from_business(cls, iat: CatalogIat, build_image_url: StimulusUrlBuilder) -> IatResponse:
        """Build one public detail response from one published IAT.

        Args:
            iat: Published IAT to expose through the API.
            build_image_url: Builder for public image URLs.

        Returns:
            The public IAT detail response.
        """
        first_pair, second_pair = iat.categories
        return cls(
            slug=iat.slug,
            title=iat.title,
            description=iat.description,
            categories=(
                CategoryPairResponse.from_business(first_pair, build_image_url),
                CategoryPairResponse.from_business(second_pair, build_image_url),
            ),
        )
