"""Runfile resolution helpers for evaluation assets."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from runfiles import Runfiles

_HARNESS_RLOCATIONPATH = "iat/apps/evaluation/browser/harness.js"


@cache
def load_browser_harness() -> str:
    """Load the browser-side harness asset from Bazel runfiles.

    Returns:
        The bundled browser harness source.

    Raises:
        FileNotFoundError: The bundled harness is unavailable.
    """
    resolver = Runfiles.Create()
    if resolver is None:
        raise FileNotFoundError("Bundled evaluation harness is missing.")

    harness_path = resolver.Rlocation(_HARNESS_RLOCATIONPATH, source_repo="")
    if harness_path is None:
        raise FileNotFoundError("Bundled evaluation harness is missing.")

    resolved_path = Path(harness_path)
    if not resolved_path.is_file():
        raise FileNotFoundError("Bundled evaluation harness is missing.")

    return resolved_path.read_text(encoding="utf-8")
