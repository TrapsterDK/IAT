"""Tests for backend frontend asset helpers."""

from __future__ import annotations

from apps.backend.frontend import resolve_frontend_dist_directory


def test_resolve_frontend_dist_directory_returns_bundled_asset_directory() -> None:
    # Given: one backend test environment with bundled frontend runfiles available.

    # When: the bundled frontend directory is resolved from runfiles.
    resolved_directory = resolve_frontend_dist_directory()

    # Then: the resolved directory exposes the built single-page app assets.
    assert resolved_directory.is_dir()
    assert (resolved_directory / "index.html").is_file()
    assert (resolved_directory / "assets" / "main.js").is_file()
