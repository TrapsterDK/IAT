"""Typed models for IAT YAML spec files."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field, model_validator

from libs.config.config import ConfigModel
from libs.pydantic.types import NonBlankString  # noqa: TC001


class StimulusSpec(BaseModel):
    """One text or image stimulus inside one IAT category."""

    model_config = ConfigDict(extra="forbid")

    text: NonBlankString | None = None
    image: Path | None = None

    @model_validator(mode="after")
    def validate_stimulus(self) -> StimulusSpec:
        """Require exactly one stimulus representation.

        Returns:
            The validated stimulus instance.
        """
        if (self.text is None) == (self.image is None):
            raise ValueError("Each stimulus must define exactly one of 'text' or 'image'.")
        return self


class CategorySpec(BaseModel):
    """One labeled category inside an IAT pair."""

    model_config = ConfigDict(extra="forbid")

    slug: NonBlankString
    label: NonBlankString
    stimuli: list[StimulusSpec] = Field(min_length=1)


class CategoryPairSpec(BaseModel):
    """One two-category block in an IAT spec."""

    model_config = ConfigDict(extra="forbid")

    category: tuple[CategorySpec, CategorySpec]

    @model_validator(mode="after")
    def validate_pair(self) -> CategoryPairSpec:
        """Require distinct category slugs per pair.

        Returns:
            The validated category pair instance.
        """
        category_slugs = [category.slug for category in self.category]
        if len(set(category_slugs)) != len(category_slugs):
            raise ValueError("Category slugs must be unique within one pair.")

        return self


class IatSpec(ConfigModel):
    """One fully validated IAT YAML definition."""

    slug: NonBlankString
    title: NonBlankString
    description: NonBlankString
    categories: tuple[CategoryPairSpec, CategoryPairSpec]

    @model_validator(mode="after")
    def validate_spec(self) -> IatSpec:
        """Require unique category slugs across the current IAT spec.

        Returns:
            The validated IAT spec instance.
        """
        category_slugs = [category.slug for pair in self.categories for category in pair.category]
        if len(set(category_slugs)) != len(category_slugs):
            raise ValueError("Category slugs must be unique within one IAT spec.")

        return self
