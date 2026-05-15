"""Shared helpers for resolving filesystem paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def resolve_path(path: Path, root: Path) -> Path:
    """Resolve one path against one root directory.

    Args:
        path: Path to resolve, relative or absolute.
        root: Root directory used for relative path resolution.

    Returns:
        The absolute resolved path.
    """
    return (path if path.is_absolute() else root / path).resolve()
