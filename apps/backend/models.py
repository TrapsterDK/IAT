"""Public API response models for IAT data."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from libs.pydantic.types import NonBlankString  # noqa: TC001


class StimulusResponse(BaseModel):
    """One public text or image stimulus returned by the backend."""

    model_config = ConfigDict(extra="forbid")

    text: NonBlankString | None = None
    image_url: NonBlankString | None = None

    @model_validator(mode="after")
    def validate_stimulus(self) -> StimulusResponse:
        """Require exactly one public stimulus representation.

        Returns:
            The validated public stimulus instance.
        """
        if (self.text is None) == (self.image_url is None):
            raise ValueError("Each stimulus must define exactly one of 'text' or 'image_url'.")

        return self


class CategoryResponse(BaseModel):
    """One labeled category in one public IAT response."""

    model_config = ConfigDict(extra="forbid")

    slug: NonBlankString
    label: NonBlankString
    stimuli: list[StimulusResponse] = Field(min_length=1)


class CategoryPairResponse(BaseModel):
    """One two-category block in one public IAT response."""

    model_config = ConfigDict(extra="forbid")

    category: tuple[CategoryResponse, CategoryResponse]


class IatSummaryResponse(BaseModel):
    """Summary metadata for one IAT."""

    model_config = ConfigDict(extra="forbid")

    slug: NonBlankString
    title: NonBlankString
    description: NonBlankString


class IatResponse(IatSummaryResponse):
    """Public response payload for one fully resolved IAT."""

    categories: tuple[CategoryPairResponse, CategoryPairResponse]
