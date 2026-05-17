"""Typed models for IAT YAML spec files."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field, model_validator

from libs.config.config import ConfigModel
from libs.path.path import resolve_path
from libs.pydantic.types import AbsoluteFilePath, NonBlankString  # noqa: TC001


class StimulusSpec(BaseModel):
    """One text or image stimulus inside one IAT category."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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

    def resolve(self, base_directory: Path) -> ResolvedStimulusSpec:
        """Resolve one stimulus against one spec directory.

        Args:
            base_directory: Directory used for relative image path resolution.

        Returns:
            The resolved stimulus instance.
        """
        if self.text is not None:
            return ResolvedStimulusSpec(text=self.text)

        if self.image is None:
            raise ValueError("Image stimuli must define one image path.")

        resolved_image_path = resolve_path(self.image, base_directory)
        if resolved_image_path.suffix.lower() != ".png":
            raise ValueError(f"Only PNG stimuli may be served: {resolved_image_path}")

        if not resolved_image_path.is_file():
            raise ValueError(f"Stimulus file does not exist: {resolved_image_path}")

        return ResolvedStimulusSpec(image=resolved_image_path)


class CategorySpec(BaseModel):
    """One labeled category inside an IAT pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: NonBlankString
    label: NonBlankString
    stimuli: tuple[StimulusSpec, ...] = Field(min_length=1)

    def resolve(self, base_directory: Path) -> ResolvedCategorySpec:
        """Resolve one category's image stimuli against one spec directory.

        Args:
            base_directory: Directory used for relative image path resolution.

        Returns:
            The resolved category instance.
        """
        return ResolvedCategorySpec(
            slug=self.slug,
            label=self.label,
            stimuli=tuple(stimulus.resolve(base_directory) for stimulus in self.stimuli),
        )


class CategoryPairSpec(BaseModel):
    """One two-category block in an IAT spec."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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

    def resolve(self, base_directory: Path) -> ResolvedCategoryPairSpec:
        """Resolve one category pair's image stimuli against one spec directory.

        Args:
            base_directory: Directory used for relative image path resolution.

        Returns:
            The resolved category pair instance.
        """
        first_category, second_category = self.category
        return ResolvedCategoryPairSpec(
            category=(
                first_category.resolve(base_directory),
                second_category.resolve(base_directory),
            )
        )


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

    def resolve(self, base_directory: Path) -> ResolvedIatSpec:
        """Resolve one IAT spec against one spec directory.

        Args:
            base_directory: Directory used for relative image path resolution.

        Returns:
            The resolved IAT spec.
        """
        first_pair, second_pair = self.categories
        return ResolvedIatSpec(
            slug=self.slug,
            title=self.title,
            description=self.description,
            categories=(
                first_pair.resolve(base_directory),
                second_pair.resolve(base_directory),
            ),
        )


class ResolvedStimulusSpec(StimulusSpec):
    """One stimulus whose image path has been resolved to one file on disk."""

    image: AbsoluteFilePath | None = None


class ResolvedCategorySpec(CategorySpec):
    """One category whose image stimuli have been resolved."""

    stimuli: tuple[ResolvedStimulusSpec, ...] = Field(min_length=1)


class ResolvedCategoryPairSpec(CategoryPairSpec):
    """One category pair whose image stimuli have been resolved."""

    category: tuple[ResolvedCategorySpec, ResolvedCategorySpec]


class ResolvedIatSpec(IatSpec):
    """One IAT spec whose image stimuli have been resolved."""

    categories: tuple[ResolvedCategoryPairSpec, ResolvedCategoryPairSpec]
