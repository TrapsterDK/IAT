"""Application service for backend IAT publication lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path, PurePosixPath

    from apps.backend.repositories.iat import (
        IatRepository,
        PublishedIat,
    )


class IatService:
    """Resolve IAT data from repository-backed backend resources."""

    def __init__(self, repository: IatRepository) -> None:
        """Initialize the IAT application service.

        Args:
            repository: Filesystem-backed IAT repository.
        """
        self._repository = repository

    def get_iats(self) -> list[PublishedIat]:
        """Return the currently available published IATs.

        Returns:
            The available published IATs.
        """
        return self._repository.get_iats()

    def get_iat(self, slug: str) -> PublishedIat | None:
        """Return one published IAT.

        Args:
            slug: Requested IAT slug.

        Returns:
            The published IAT, or `None` when unavailable.
        """
        return self._repository.get_iat(slug)

    def get_stimulus(self, image: PurePosixPath) -> Path | None:
        """Resolve one public PNG request through the repository.

        Args:
            image: Published public image path.

        Returns:
            The resolved PNG path, or `None` when invalid.
        """
        return self._repository.get_stimuli(image)
