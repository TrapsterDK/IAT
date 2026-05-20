"""Frontend asset helpers."""

from __future__ import annotations

from pathlib import Path

from runfiles import Runfiles

_FRONTEND_DIST_RLOCATIONPATH = "iat/apps/frontend/dist"


def resolve_frontend_dist_directory() -> Path:
    """Resolve the built frontend `dist/` directory from Bazel runfiles.

    Returns:
        The resolved frontend distribution directory.

    Raises:
        FileNotFoundError: The built frontend distribution directory is unavailable.
    """
    resolver = Runfiles.Create()
    if resolver is None:
        raise FileNotFoundError("Bundled frontend asset directory is missing.")

    frontend_dist = resolver.Rlocation(_FRONTEND_DIST_RLOCATIONPATH, source_repo="")
    if frontend_dist is None:
        raise FileNotFoundError("Bundled frontend asset directory is missing.")

    frontend_dist_path = Path(frontend_dist)
    if not frontend_dist_path.is_dir():
        raise FileNotFoundError("Bundled frontend asset directory is missing.")

    return frontend_dist_path
