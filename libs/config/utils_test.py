"""Tests for shared config utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from libs.config.exceptions import ExtendingConfigError, ExtendingConfigPathError
from libs.config.utils import ConfigFormat, detect_config_format, read_mapping_file, write_mapping_file


@pytest.mark.parametrize(
    ("file_name", "expected_format"),
    [
        pytest.param("config.yaml", ConfigFormat.YAML, id="yaml"),
        pytest.param("config.yml", ConfigFormat.YAML, id="yml"),
        pytest.param("config.json", ConfigFormat.JSON, id="json"),
        pytest.param("config.toml", ConfigFormat.TOML, id="toml"),
        pytest.param("CONFIG.YAML", ConfigFormat.YAML, id="uppercase-suffix"),
    ],
)
def test_detect_config_format_supports_expected_suffixes(file_name: str, expected_format: ConfigFormat) -> None:
    # Given: one config file path with a supported suffix.
    config_path = Path(file_name)

    # When: the suffix is inspected.
    resolved_format = detect_config_format(config_path)

    # Then: the expected config format is returned.
    assert resolved_format == expected_format


def test_detect_config_format_rejects_unsupported_suffix() -> None:
    # Given: one config file path with an unsupported suffix.
    config_path = Path("config.ini")

    # When: the suffix is inspected.
    # Then: the unsupported format is rejected.
    with pytest.raises(ExtendingConfigError):
        detect_config_format(config_path)


@pytest.mark.parametrize(
    ("file_name", "file_contents", "expected_mapping"),
    [
        pytest.param("config.yaml", "name: yaml\ncount: 1\n", {"name": "yaml", "count": 1}, id="yaml"),
        pytest.param(
            "config.json",
            '{"name": "json", "count": 2}',
            {"name": "json", "count": 2},
            id="json",
        ),
        pytest.param("config.toml", 'name = "toml"\ncount = 3\n', {"name": "toml", "count": 3}, id="toml"),
    ],
)
def test_read_mapping_file_decodes_supported_formats(
    tmp_path: Path,
    file_name: str,
    file_contents: str,
    expected_mapping: dict[str, object],
) -> None:
    # Given: one config file in a supported format.
    config_path = tmp_path / file_name
    config_path.write_text(file_contents, encoding="utf-8")

    # When: the mapping file is read directly.
    resolved_mapping = read_mapping_file(config_path)

    # Then: the decoded mapping is returned.
    assert resolved_mapping == expected_mapping


def test_read_mapping_file_returns_empty_mapping_for_yaml_null(tmp_path: Path) -> None:
    # Given: one YAML file that decodes to null.
    config_path = tmp_path / "config.yaml"
    config_path.write_text("null\n", encoding="utf-8")

    # When: the mapping file is read directly.
    resolved_mapping = read_mapping_file(config_path)

    # Then: the loader normalizes the payload to an empty mapping.
    assert resolved_mapping == {}


def test_read_mapping_file_rejects_non_string_yaml_keys(tmp_path: Path) -> None:
    # Given: one YAML file with a mapping key that does not decode to a string.
    config_path = tmp_path / "config.yaml"
    config_path.write_text("1: value\n", encoding="utf-8")

    # When: the mapping file is read directly.
    # Then: the loader rejects non-string mapping keys.
    with pytest.raises(ExtendingConfigError):
        read_mapping_file(config_path)


@pytest.mark.parametrize(
    ("file_name", "file_contents"),
    [
        pytest.param("config.yaml", "- one\n- two\n", id="yaml-list"),
        pytest.param("config.json", json.dumps([1, 2, 3]), id="json-list"),
    ],
)
def test_read_mapping_file_rejects_non_mapping_payloads(
    tmp_path: Path,
    file_name: str,
    file_contents: str,
) -> None:
    # Given: one config file that decodes to a non-mapping payload.
    config_path = tmp_path / file_name
    config_path.write_text(file_contents, encoding="utf-8")

    # When: the mapping file is read directly.
    # Then: the non-mapping payload is rejected.
    with pytest.raises(ExtendingConfigError):
        read_mapping_file(config_path)


def test_read_mapping_file_rejects_missing_file(tmp_path: Path) -> None:
    # Given: one missing config file path.
    missing_path = tmp_path / "missing.yaml"

    # When: the mapping file is read directly.
    # Then: the missing path is rejected.
    with pytest.raises(ExtendingConfigPathError):
        read_mapping_file(missing_path)


def test_read_mapping_file_rejects_directory_path(tmp_path: Path) -> None:
    # Given: one directory path instead of one config file.
    directory_path = tmp_path / "config-dir.json"
    directory_path.mkdir()

    # When: the mapping file is read directly.
    # Then: the directory path is rejected.
    with pytest.raises(ExtendingConfigPathError):
        read_mapping_file(directory_path)


@pytest.mark.parametrize(
    ("config_format", "file_contents", "expected_mapping"),
    [
        pytest.param(
            ConfigFormat.YAML,
            "name: yaml\ncount: 1\n",
            {"name": "yaml", "count": 1},
            id="yaml-explicit-format",
        ),
        pytest.param(
            ConfigFormat.JSON,
            '{"name": "json", "count": 2}',
            {"name": "json", "count": 2},
            id="json-explicit-format",
        ),
        pytest.param(
            ConfigFormat.TOML,
            'name = "toml"\ncount = 3\n',
            {"name": "toml", "count": 3},
            id="toml-explicit-format",
        ),
    ],
)
def test_read_mapping_file_uses_explicit_format_override(
    tmp_path: Path,
    config_format: ConfigFormat,
    file_contents: str,
    expected_mapping: dict[str, object],
) -> None:
    # Given: one config input path with an unsupported suffix and one explicit config format.
    config_path = tmp_path / "config.data"
    config_path.write_text(file_contents, encoding="utf-8")

    # When: the mapping file is read directly with the explicit format override.
    resolved_mapping = read_mapping_file(config_path, config_format)

    # Then: the explicit format controls decoding even though the file suffix is unsupported.
    assert resolved_mapping == expected_mapping


@pytest.mark.parametrize(
    ("file_name", "payload", "expected_mapping"),
    [
        pytest.param("config.yaml", {"name": "yaml", "count": 1}, {"name": "yaml", "count": 1}, id="yaml"),
        pytest.param("config.json", {"name": "json", "count": 2}, {"name": "json", "count": 2}, id="json"),
        pytest.param("config.toml", {"name": "toml", "count": 3}, {"name": "toml", "count": 3}, id="toml"),
    ],
)
def test_write_mapping_file_writes_supported_formats(
    tmp_path: Path,
    file_name: str,
    payload: dict[str, object],
    expected_mapping: dict[str, object],
) -> None:
    # Given: one supported config output path and one mapping payload.
    output_path = tmp_path / file_name

    # When: the mapping file is written directly.
    write_mapping_file(output_path, payload)

    # Then: the file round-trips through the mapping reader.
    assert read_mapping_file(output_path) == expected_mapping


def test_write_mapping_file_rejects_directory_path(tmp_path: Path) -> None:
    # Given: one directory path instead of one config output file path.
    output_path = tmp_path / "config-dir.json"
    output_path.mkdir()

    # When: the mapping file is written directly.
    # Then: the directory path is rejected.
    with pytest.raises(ExtendingConfigPathError):
        write_mapping_file(output_path, {"name": "json"})


def test_write_mapping_file_rejects_missing_parent_directory(tmp_path: Path) -> None:
    # Given: one config output file path under a missing parent directory.
    output_path = tmp_path / "nested" / "config.json"

    # When: the mapping file is written directly.
    # Then: the missing parent directory is rejected.
    with pytest.raises(ExtendingConfigPathError, match="parent directory"):
        write_mapping_file(output_path, {"name": "json"})


def test_write_mapping_file_rejects_unsupported_suffix(tmp_path: Path) -> None:
    # Given: one unsupported config output file extension.
    output_path = tmp_path / "config.ini"

    # When: the mapping file is written directly.
    # Then: the unsupported format is rejected.
    with pytest.raises(ExtendingConfigError):
        write_mapping_file(output_path, {"name": "json"})


def test_write_mapping_file_rejects_unserializable_payload(tmp_path: Path) -> None:
    # Given: one supported config output path and one payload with an unserializable value.
    output_path = tmp_path / "config.json"

    # When: the mapping file is written directly.
    # Then: the unserializable payload is rejected.
    with pytest.raises(ExtendingConfigError, match="cannot be serialized"):
        write_mapping_file(output_path, {"name": {1, 2, 3}})


@pytest.mark.parametrize(
    ("config_format", "payload"),
    [
        pytest.param(ConfigFormat.YAML, {"name": "yaml", "count": 1}, id="yaml-explicit-format"),
        pytest.param(ConfigFormat.JSON, {"name": "json", "count": 2}, id="json-explicit-format"),
        pytest.param(ConfigFormat.TOML, {"name": "toml", "count": 3}, id="toml-explicit-format"),
    ],
)
def test_write_mapping_file_uses_explicit_format_override(
    tmp_path: Path,
    config_format: ConfigFormat,
    payload: dict[str, object],
) -> None:
    # Given: one config output path with an unsupported suffix and one explicit config format.
    output_path = tmp_path / "config.data"

    # When: the mapping file is written directly with the explicit format override.
    write_mapping_file(output_path, payload, config_format)

    # Then: the explicit format controls serialization and decoding even though the file suffix is unsupported.
    assert read_mapping_file(output_path, config_format) == payload
