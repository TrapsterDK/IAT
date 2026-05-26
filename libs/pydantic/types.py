"""Shared Pydantic type aliases."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, DirectoryPath, FilePath, StringConstraints


def _absolute_path(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")

    return path


def _validate_unique_items[T](values: T) -> T:
    if not isinstance(values, Collection):
        raise TypeError(f"Expected a collection for uniqueness validation, got {type(values).__name__}.")

    try:
        unique_values = len(set(values))
    except TypeError as exc:
        raise TypeError("Collection items must be hashable for uniqueness validation.") from exc

    if unique_values != len(values):
        raise ValueError("Collection items must be unique.")

    return values


def _validate_unique_unhashable_items[T](values: T) -> T:
    if not isinstance(values, Collection):
        raise TypeError(f"Expected a collection for uniqueness validation, got {type(values).__name__}.")

    try:
        _validate_unique_items(values)
    except TypeError:
        seen = []
        for item in values:
            if item in seen:
                raise ValueError("Collection items must be unique.")  # noqa: B904
            seen.append(item)

    return values


type NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type NonBlankString255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
type Slug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
    ),
]
type AbsolutePath = Annotated[Path, AfterValidator(_absolute_path)]
type AbsoluteDirectoryPath = Annotated[DirectoryPath, AfterValidator(_absolute_path)]
type AbsoluteFilePath = Annotated[FilePath, AfterValidator(_absolute_path)]
type UniqueHashable[T] = Annotated[T, AfterValidator(_validate_unique_items)]
type UniqueUnhashable[T] = Annotated[T, AfterValidator(_validate_unique_unhashable_items)]
