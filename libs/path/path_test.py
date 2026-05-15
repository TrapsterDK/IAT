"""Tests for shared path-resolution helpers."""

from __future__ import annotations

from pathlib import Path

from libs.path.path import resolve_path


def test_resolve_path_resolves_relative_path_against_root(tmp_path: Path) -> None:
    # Given: one root directory with one relative configured path.
    root = tmp_path
    expected_path = tmp_path / "resources/iats"

    # When: the configured path is resolved.
    resolved_path = resolve_path(Path("resources/iats"), root)

    # Then: the relative path resolves below the root directory.
    assert resolved_path == expected_path.resolve()


def test_resolve_path_preserves_absolute_path(tmp_path: Path) -> None:
    # Given: one absolute path.
    configured_path = tmp_path / "resources/stimuli"

    # When: the configured path is resolved.
    resolved_path = resolve_path(configured_path, tmp_path / "ignored")

    # Then: the absolute path is returned unchanged except for normalization.
    assert resolved_path == configured_path.resolve()
