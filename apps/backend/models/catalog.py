"""Catalog IAT models shared across backend layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import PurePosixPath

    from libs.pydantic.types import Slug


@dataclass(frozen=True, slots=True)
class CatalogStimulus:
    """One text or publicly exposed image stimulus."""

    text: str | None = None
    image_path: PurePosixPath | None = None


@dataclass(frozen=True, slots=True)
class CatalogCategory:
    """One catalog category in one IAT."""

    slug: Slug
    label: str
    stimuli: tuple[CatalogStimulus, ...]


type CatalogCategoryPair = tuple[CatalogCategory, CatalogCategory]


@dataclass(frozen=True, slots=True)
class CatalogIat:
    """One catalog IAT with public stimulus paths."""

    slug: Slug
    title: str
    description: str
    categories: tuple[CatalogCategoryPair, CatalogCategoryPair]
