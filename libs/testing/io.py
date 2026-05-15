"""Shared file-writing helpers for tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


TEST_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write one JSON test fixture to disk.

    Args:
        path: Output file path.
        payload: JSON-serializable payload to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    """Write one YAML test fixture to disk.

    Args:
        path: Output file path.
        payload: YAML-serializable payload to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def write_png(path: Path) -> None:
    """Write one minimal PNG signature to disk for tests.

    Args:
        path: Output file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(TEST_PNG_SIGNATURE)
