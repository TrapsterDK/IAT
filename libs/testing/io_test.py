"""Tests for shared test file-writing helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from libs.testing.io import TEST_PNG_SIGNATURE, write_json, write_png, write_yaml

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_write_json_writes_indented_json_with_trailing_newline(tmp_path: Path) -> None:
    # Given: one target JSON file path and one mapping payload.
    output_path = tmp_path / "fixture.json"
    payload = {"slug": "sample-iat", "count": 2}

    # When: the shared JSON writer writes the fixture.
    write_json(output_path, payload)

    # Then: the file contains the expected indented JSON plus one trailing newline.
    assert output_path.read_text(encoding="utf-8") == json.dumps(payload, indent=2) + "\n"


def test_write_yaml_preserves_mapping_order(tmp_path: Path) -> None:
    # Given: one target YAML file path and one ordered mapping payload.
    output_path = tmp_path / "fixture.yaml"
    payload = {"second": "beta", "first": "alpha"}

    # When: the shared YAML writer writes the fixture.
    write_yaml(output_path, payload)

    # Then: the file preserves insertion order instead of sorting keys.
    assert output_path.read_text(encoding="utf-8") == "second: beta\nfirst: alpha\n"


def test_write_png_writes_png_signature(tmp_path: Path) -> None:
    # Given: one target PNG file path.
    output_path = tmp_path / "fixture.png"

    # When: the shared PNG writer writes the fixture.
    write_png(output_path)

    # Then: the file contains the expected PNG signature bytes.
    assert output_path.read_bytes() == TEST_PNG_SIGNATURE


@pytest.mark.parametrize(
    "writer",
    [
        pytest.param(lambda path: write_json(path, {"slug": "sample-iat", "count": 2}), id="json"),
        pytest.param(lambda path: write_yaml(path, {"slug": "sample-iat", "count": 2}), id="yaml"),
        pytest.param(write_png, id="png"),
    ],
)
def test_file_writers_create_missing_parent_directory(
    tmp_path: Path,
    writer: Callable[[Path], None],
) -> None:
    # Given: one output path whose parent directory does not exist.
    output_path = tmp_path / "missing" / "fixture.data"

    # When: one shared file writer is used.
    writer(output_path)

    # Then: the writer creates the parent directory automatically.
    assert output_path.parent.is_dir()
    assert output_path.is_file()
