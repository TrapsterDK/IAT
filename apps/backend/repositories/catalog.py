"""Filesystem-backed repository for the published IAT catalog."""

from __future__ import annotations

import base64
import hashlib
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from apps.backend.domain.iat.spec_models import IatSpec, ResolvedCategorySpec, ResolvedIatSpec, ResolvedStimulusSpec
from apps.backend.models.catalog import CatalogCategory, CatalogIat, CatalogStimulus

if TYPE_CHECKING:
    from pathlib import Path

    from apps.backend.settings import ResolvedIatResources


class CatalogRepository:
    """Read and publish IAT definitions from the configured catalog."""

    def __init__(self, settings: ResolvedIatResources) -> None:
        """Initialize the filesystem-backed catalog repository.

        Args:
            settings: Resolved backend resource settings.
        """
        self._slug_to_iat: dict[str, CatalogIat] = {}
        self._image_remote_to_source: dict[PurePosixPath, Path] = {}
        self._load_iats(settings.iats)

    def get_iats(self) -> list[CatalogIat]:
        """List the currently configured IATs.

        Returns:
            The configured published IATs in catalog order.
        """
        return list(self._slug_to_iat.values())

    def get_iat(self, slug: str) -> CatalogIat | None:
        """Return one preloaded IAT by slug.

        Args:
            slug: Requested IAT slug.

        Returns:
            The published IAT, or `None` when unavailable.
        """
        return self._slug_to_iat.get(slug)

    def get_published_stimuli(self) -> dict[PurePosixPath, Path]:
        """Return the published image-path mapping used by the stimulus repository.

        Returns:
            One copy of the published stimulus-path mapping.
        """
        return dict(self._image_remote_to_source)

    def get_stimulus(self, image: PurePosixPath) -> Path | None:
        """Resolve one published public image path into one source file.

        Args:
            image: Published public image path.

        Returns:
            The resolved source image path, or `None` when unavailable.
        """
        return self._image_remote_to_source.get(image)

    def _load_iats(self, spec_paths: tuple[Path, ...]) -> None:
        for spec_path in spec_paths:
            iat_spec = IatSpec.from_yaml_file(spec_path).resolve(base_directory=spec_path.parent)
            if iat_spec.slug in self._slug_to_iat:
                raise ValueError("IAT slugs must be unique across the configured repository.")

            self._slug_to_iat[iat_spec.slug] = self._publish_iat(iat_spec)

    def _publish_iat(self, iat_spec: ResolvedIatSpec) -> CatalogIat:
        first_pair, second_pair = iat_spec.categories
        first_left, first_right = first_pair.category
        second_left, second_right = second_pair.category
        return CatalogIat(
            slug=iat_spec.slug,
            title=iat_spec.title,
            description=iat_spec.description,
            categories=(
                (
                    self._publish_category(iat_spec.slug, first_left),
                    self._publish_category(iat_spec.slug, first_right),
                ),
                (
                    self._publish_category(iat_spec.slug, second_left),
                    self._publish_category(iat_spec.slug, second_right),
                ),
            ),
        )

    def _publish_category(self, iat_slug: str, category: ResolvedCategorySpec) -> CatalogCategory:
        return CatalogCategory(
            slug=category.slug,
            label=category.label,
            stimuli=tuple(self._publish_stimulus(iat_slug, category.slug, stimulus) for stimulus in category.stimuli),
        )

    def _publish_stimulus(
        self,
        iat_slug: str,
        category_slug: str,
        stimulus: ResolvedStimulusSpec,
    ) -> CatalogStimulus:
        if stimulus.text is not None:
            return CatalogStimulus(text=stimulus.text)

        if stimulus.image is None:
            raise ValueError("Image stimuli must define one image path.")

        hashed_source_path = hashlib.sha256(str(stimulus.image).encode("utf-8")).digest()
        image_key = base64.urlsafe_b64encode(hashed_source_path).decode("ascii").rstrip("=")
        image = PurePosixPath(f"{iat_slug}/{category_slug}/{image_key}.png")
        existing_source_path = self._image_remote_to_source.setdefault(image, stimulus.image)
        if existing_source_path != stimulus.image:
            raise ValueError(f"Public stimulus path must be unique: {image.as_posix()}")

        return CatalogStimulus(image_path=image)
