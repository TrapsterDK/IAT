"""Typed models for IAT YAML spec files."""

from __future__ import annotations

import pathlib

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from libs.config.config import ConfigModel


class StimulusSpec(BaseModel):
    """One text or image stimulus inside one IAT category."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    image: pathlib.Path | None = None

    @field_validator("text")
    @classmethod
    def validate_text_value(cls, value: str | None) -> str | None:
        """Reject blank text stimuli while preserving provided values.

        Args:
            value: Candidate text value from the YAML payload.

        Returns:
            The original value, or `None` when the field is unset.
        """
        if value is None:
            return None
        if not value.strip():
            raise ValueError("Stimulus values must not be blank.")
        return value

    @field_validator("image", mode="before")
    @classmethod
    def validate_image_value(cls, value: pathlib.Path | str | None) -> pathlib.Path | str | None:
        """Reject blank image stimuli while preserving provided values.

        Args:
            value: Candidate image value from the YAML payload.

        Returns:
            The original value, or `None` when the field is unset.
        """
        if value is None:
            return None
        if isinstance(value, pathlib.Path):
            return value
        if isinstance(value, str) and not value.strip():
            raise ValueError("Stimulus values must not be blank.")
        return value

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

    slug: str
    label: str
    stimuli: list[StimulusSpec]

    @field_validator("slug", "label")
    @classmethod
    def validate_string_field(cls, value: str) -> str:
        """Reject blank category string fields.

        Args:
            value: Candidate category slug or label.

        Returns:
            The original non-blank string value.
        """
        if not value.strip():
            raise ValueError("Category fields must not be blank.")
        return value

    @model_validator(mode="after")
    def validate_category(self) -> CategorySpec:
        """Require at least one stimulus in each category.

        Returns:
            The validated category instance.
        """
        if not self.stimuli:
            raise ValueError("Each category must contain at least one stimulus.")
        return self


class CategoryPairSpec(BaseModel):
    """One two-category block in an IAT spec."""

    model_config = ConfigDict(extra="forbid")

    category: tuple[CategorySpec, CategorySpec]

    @model_validator(mode="after")
    def validate_pair(self) -> CategoryPairSpec:
        """Require exactly two distinct categories per pair.

        Returns:
            The validated category pair instance.
        """
        category_slugs = [category.slug for category in self.category]
        if len(set(category_slugs)) != len(category_slugs):
            raise ValueError("Category slugs must be unique within one pair.")

        return self


class IatSpec(ConfigModel):
    """One fully validated IAT YAML definition."""

    slug: str
    title: str
    description: str
    categories: tuple[CategoryPairSpec, CategoryPairSpec]

    @field_validator("slug", "title", "description")
    @classmethod
    def validate_string_field(cls, value: str) -> str:
        """Reject blank top-level IAT string fields.

        Args:
            value: Candidate top-level slug, title, or description value.

        Returns:
            The original non-blank string value.
        """
        if not value.strip():
            raise ValueError("IAT fields must not be blank.")
        return value

    @model_validator(mode="after")
    def validate_spec(self) -> IatSpec:
        """Require the current two-pair IAT shape and unique category slugs.

        Returns:
            The validated IAT spec instance.
        """
        category_slugs = [category.slug for pair in self.categories for category in pair.category]
        if len(set(category_slugs)) != len(category_slugs):
            raise ValueError("Category slugs must be unique within one IAT spec.")

        return self
