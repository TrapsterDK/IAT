"""Application service for published IAT catalog lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path, PurePosixPath

    from apps.backend.models.catalog import CatalogIat
    from apps.backend.repositories.catalog import CatalogRepository


class CatalogService:
    """Resolve published IAT data from catalog repositories."""

    def __init__(self, catalog_repository: CatalogRepository) -> None:
        """Initialize the catalog application service.

        Args:
            catalog_repository: Published catalog repository.
        """
        self._catalog_repository = catalog_repository

    def get_iats(self) -> list[CatalogIat]:
        """Return the currently available published IATs.

        Returns:
            The available published IATs.
        """
        return self._catalog_repository.get_iats()

    def get_iat(self, slug: str) -> CatalogIat | None:
        """Return one published IAT.

        Args:
            slug: Requested IAT slug.

        Returns:
            The published IAT, or `None` when unavailable.
        """
        return self._catalog_repository.get_iat(slug)

    def get_stimulus(self, image: PurePosixPath) -> Path | None:
        """Resolve one public PNG request through the repository.

        Args:
            image: Published public image path.

        Returns:
            The resolved PNG path, or `None` when invalid.
        """
        return self._catalog_repository.get_stimulus(image)
