"""Published IAT domain models exposed beyond the repository boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import PurePosixPath


@dataclass(frozen=True, slots=True)
class PublishedStimulus:
    """One text or publicly exposed image stimulus."""

    text: str | None = None
    image_path: PurePosixPath | None = None


@dataclass(frozen=True, slots=True)
class PublishedCategory:
    """One published category in one IAT."""

    slug: str
    label: str
    stimuli: tuple[PublishedStimulus, ...]


type PublishedCategoryPair = tuple[PublishedCategory, PublishedCategory]


@dataclass(frozen=True, slots=True)
class PublishedIat:
    """One published IAT with public stimulus paths."""

    slug: str
    title: str
    description: str
    categories: tuple[PublishedCategoryPair, PublishedCategoryPair]
