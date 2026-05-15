"""Tests for plain file-backed config models without inheritance."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from libs.config.config import ConfigModel
from libs.config.exceptions import ExtendingConfigError, ExtendingConfigPathError

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("file_name", "file_contents", "expected_name", "expected_count"),
    [
        pytest.param("config.yaml", "name: yaml\ncount: 1\n", "yaml", 1, id="yaml"),
        pytest.param("config.json", '{"name": "json", "count": 2}', "json", 2, id="json"),
        pytest.param("config.toml", 'name = "toml"\ncount = 3\n', "toml", 3, id="toml"),
    ],
)
def test_config_model_loads_each_supported_file_format(
    tmp_path: Path,
    file_name: str,
    file_contents: str,
    expected_name: str,
    expected_count: int,
) -> None:
    # Given: one config file in a supported format.
    config_path = tmp_path / file_name
    config_path.write_text(file_contents, encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    # When: the generic file loader is used.
    resolved_config = ExampleConfig.from_file(config_path)

    # Then: the file is decoded and validated as one config model.
    assert resolved_config.name == expected_name
    assert resolved_config.count == expected_count


def test_config_model_supports_yaml_explicit_loader(tmp_path: Path) -> None:
    # Given: one YAML config file.
    config_path = tmp_path / "config.yaml"
    config_path.write_text("name: yaml\ncount: 1\n", encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    # When: the YAML-specific loader is used.
    resolved_config = ExampleConfig.from_yaml_file(config_path)

    # Then: the file is decoded and validated as one config model.
    assert resolved_config.name == "yaml"
    assert resolved_config.count == 1


def test_config_model_supports_json_explicit_loader(tmp_path: Path) -> None:
    # Given: one JSON config file.
    config_path = tmp_path / "config.json"
    config_path.write_text('{"name": "json", "count": 2}', encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    # When: the JSON-specific loader is used.
    resolved_config = ExampleConfig.from_json_file(config_path)

    # Then: the file is decoded and validated as one config model.
    assert resolved_config.name == "json"
    assert resolved_config.count == 2


def test_config_model_supports_toml_explicit_loader(tmp_path: Path) -> None:
    # Given: one TOML config file.
    config_path = tmp_path / "config.toml"
    config_path.write_text('name = "toml"\ncount = 3\n', encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    # When: the TOML-specific loader is used.
    resolved_config = ExampleConfig.from_toml_file(config_path)

    # Then: the file is decoded and validated as one config model.
    assert resolved_config.name == "toml"
    assert resolved_config.count == 3


def test_config_model_yaml_loader_uses_explicit_format_override(tmp_path: Path) -> None:
    # Given: one YAML config file stored under an unsupported suffix.
    config_path = tmp_path / "config.data"
    config_path.write_text("name: yaml\ncount: 1\n", encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    # When: the YAML-specific loader is used.
    resolved_config = ExampleConfig.from_yaml_file(config_path)

    # Then: the explicit loader decodes the file as YAML despite the unsupported suffix.
    assert resolved_config.name == "yaml"
    assert resolved_config.count == 1


def test_config_model_json_loader_uses_explicit_format_override(tmp_path: Path) -> None:
    # Given: one JSON config file stored under an unsupported suffix.
    config_path = tmp_path / "config.data"
    config_path.write_text('{"name": "json", "count": 2}', encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    # When: the JSON-specific loader is used.
    resolved_config = ExampleConfig.from_json_file(config_path)

    # Then: the explicit loader decodes the file as JSON despite the unsupported suffix.
    assert resolved_config.name == "json"
    assert resolved_config.count == 2


def test_config_model_toml_loader_uses_explicit_format_override(tmp_path: Path) -> None:
    # Given: one TOML config file stored under an unsupported suffix.
    config_path = tmp_path / "config.data"
    config_path.write_text('name = "toml"\ncount = 3\n', encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    # When: the TOML-specific loader is used.
    resolved_config = ExampleConfig.from_toml_file(config_path)

    # Then: the explicit loader decodes the file as TOML despite the unsupported suffix.
    assert resolved_config.name == "toml"
    assert resolved_config.count == 3


def test_config_model_raises_for_missing_file(tmp_path: Path) -> None:
    # Given: one missing config file path.
    missing_path = tmp_path / "missing.yaml"

    class ExampleConfig(ConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader reports the missing path.
    with pytest.raises(ExtendingConfigPathError):
        ExampleConfig.from_file(missing_path)


def test_config_model_yaml_loader_raises_for_missing_file(tmp_path: Path) -> None:
    # Given: one missing YAML config file path.
    missing_path = tmp_path / "missing.yaml"

    class ExampleConfig(ConfigModel):
        name: str

    # When: the YAML-specific loader is used.
    # Then: the loader reports the missing path.
    with pytest.raises(ExtendingConfigPathError):
        ExampleConfig.from_yaml_file(missing_path)


def test_config_model_json_loader_raises_for_missing_file(tmp_path: Path) -> None:
    # Given: one missing JSON config file path.
    missing_path = tmp_path / "missing.json"

    class ExampleConfig(ConfigModel):
        name: str

    # When: the JSON-specific loader is used.
    # Then: the loader reports the missing path.
    with pytest.raises(ExtendingConfigPathError):
        ExampleConfig.from_json_file(missing_path)


def test_config_model_toml_loader_raises_for_missing_file(tmp_path: Path) -> None:
    # Given: one missing TOML config file path.
    missing_path = tmp_path / "missing.toml"

    class ExampleConfig(ConfigModel):
        name: str

    # When: the TOML-specific loader is used.
    # Then: the loader reports the missing path.
    with pytest.raises(ExtendingConfigPathError):
        ExampleConfig.from_toml_file(missing_path)


def test_config_model_raises_for_directory_path(tmp_path: Path) -> None:
    # Given: one directory path instead of one config file.
    directory_path = tmp_path / "config-dir.json"
    directory_path.mkdir()

    class ExampleConfig(ConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the directory path.
    with pytest.raises(ExtendingConfigPathError):
        ExampleConfig.from_file(directory_path)


def test_config_model_raises_for_non_mapping_payload(tmp_path: Path) -> None:
    # Given: one config file that decodes to a list.
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the non-mapping payload.
    with pytest.raises(ExtendingConfigError):
        ExampleConfig.from_file(config_path)


@pytest.mark.parametrize(
    ("file_name", "file_contents"),
    [
        pytest.param("config.yaml", "- one\n- two\n", id="yaml-list"),
        pytest.param("config.json", json.dumps([1, 2, 3]), id="json-list"),
    ],
)
def test_config_model_rejects_non_mapping_payloads_before_validation(
    tmp_path: Path,
    file_name: str,
    file_contents: str,
) -> None:
    # Given: config files that decode to a non-mapping payload.
    config_path = tmp_path / file_name
    config_path.write_text(file_contents, encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str

    # When: the file loader is used.
    # Then: decoding rejects the non-mapping payload before model validation runs.
    with pytest.raises(ExtendingConfigError):
        ExampleConfig.from_file(config_path)


def test_config_model_validation_runs_after_mapping_file_loading(tmp_path: Path) -> None:
    # Given: one TOML config file that decodes to a mapping but still fails schema validation.
    config_path = tmp_path / "config.toml"
    config_path.write_text("items = [1, 2]\n", encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str

    # When: the file loader is used.
    # Then: model validation runs on the decoded mapping payload.
    with pytest.raises(ValidationError):
        ExampleConfig.from_file(config_path)


def test_config_model_rejects_unsupported_suffix(tmp_path: Path) -> None:
    # Given: one unsupported config file extension.
    config_path = tmp_path / "config.ini"
    config_path.write_text("name=value\n", encoding="utf-8")

    class ExampleConfig(ConfigModel):
        name: str

    # When: the generic file loader is used.
    # Then: the loader rejects the unsupported file format.
    with pytest.raises(ExtendingConfigError):
        ExampleConfig.from_file(config_path)


def test_config_model_writes_one_stable_json_file(tmp_path: Path) -> None:
    # Given: one validated config model and one JSON output path.
    output_path = tmp_path / "config.json"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="json", count=2)

    # When: the config model is written to disk as JSON.
    resolved_config.to_json_file(output_path)

    # Then: the JSON file is created with stable formatting and round-trips through the loader.
    assert output_path.read_text(encoding="utf-8") == '{\n  "count": 2,\n  "name": "json"\n}\n'
    assert ExampleConfig.from_json_file(output_path) == resolved_config


def test_config_model_rejects_missing_parent_directory_when_writing_json(tmp_path: Path) -> None:
    # Given: one validated config model and one JSON output path under a missing parent directory.
    output_path = tmp_path / "nested" / "config.json"

    class ExampleConfig(ConfigModel):
        name: str

    resolved_config = ExampleConfig(name="json")

    # When: the config model is written to disk as JSON.
    # Then: the missing parent directory is rejected.
    with pytest.raises(ExtendingConfigPathError, match="parent directory"):
        resolved_config.to_json_file(output_path)


def test_config_model_rejects_missing_parent_directory_when_writing_generic_file(tmp_path: Path) -> None:
    # Given: one validated config model and one generic output path under a missing parent directory.
    output_path = tmp_path / "nested" / "config.json"

    class ExampleConfig(ConfigModel):
        name: str

    resolved_config = ExampleConfig(name="json")

    # When: the config model is written through the generic writer.
    # Then: the missing parent directory is rejected.
    with pytest.raises(ExtendingConfigPathError, match="parent directory"):
        resolved_config.to_file(output_path)


def test_config_model_writes_yaml_with_explicit_writer_on_unsupported_suffix(tmp_path: Path) -> None:
    # Given: one validated config model and one output path with an unsupported suffix.
    output_path = tmp_path / "config.data"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the YAML-specific writer is used.
    resolved_config.to_yaml_file(output_path)

    # Then: the file still round-trips through the YAML-specific loader.
    assert ExampleConfig.from_yaml_file(output_path) == resolved_config


def test_config_model_writes_json_with_explicit_writer_on_unsupported_suffix(tmp_path: Path) -> None:
    # Given: one validated config model and one output path with an unsupported suffix.
    output_path = tmp_path / "config.data"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the JSON-specific writer is used.
    resolved_config.to_json_file(output_path)

    # Then: the file still round-trips through the JSON-specific loader.
    assert ExampleConfig.from_json_file(output_path) == resolved_config


def test_config_model_writes_toml_with_explicit_writer_on_unsupported_suffix(tmp_path: Path) -> None:
    # Given: one validated config model and one output path with an unsupported suffix.
    output_path = tmp_path / "config.data"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the TOML-specific writer is used.
    resolved_config.to_toml_file(output_path)

    # Then: the file still round-trips through the TOML-specific loader.
    assert ExampleConfig.from_toml_file(output_path) == resolved_config


def test_config_model_writes_yaml_with_explicit_writer(tmp_path: Path) -> None:
    # Given: one validated config model and one YAML output file path.
    output_path = tmp_path / "config.yaml"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the YAML-specific writer is used.
    resolved_config.to_yaml_file(output_path)

    # Then: the written file round-trips through the config loader.
    assert ExampleConfig.from_file(output_path) == resolved_config


def test_config_model_writes_json_with_explicit_writer(tmp_path: Path) -> None:
    # Given: one validated config model and one JSON output file path.
    output_path = tmp_path / "config.json"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the JSON-specific writer is used.
    resolved_config.to_json_file(output_path)

    # Then: the written file round-trips through the config loader.
    assert ExampleConfig.from_file(output_path) == resolved_config


def test_config_model_writes_toml_with_explicit_writer(tmp_path: Path) -> None:
    # Given: one validated config model and one TOML output file path.
    output_path = tmp_path / "config.toml"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the TOML-specific writer is used.
    resolved_config.to_toml_file(output_path)

    # Then: the written file round-trips through the config loader.
    assert ExampleConfig.from_file(output_path) == resolved_config


def test_config_model_writes_yaml_with_generic_writer(tmp_path: Path) -> None:
    # Given: one validated config model and one YAML output file path.
    output_path = tmp_path / "config.yaml"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the generic writer is used for a YAML file.
    resolved_config.to_file(output_path)

    # Then: the written file round-trips through the config loader.
    assert ExampleConfig.from_file(output_path) == resolved_config


def test_config_model_writes_json_with_generic_writer(tmp_path: Path) -> None:
    # Given: one validated config model and one JSON output file path.
    output_path = tmp_path / "config.json"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the generic writer is used for a JSON file.
    resolved_config.to_file(output_path)

    # Then: the written file round-trips through the config loader.
    assert ExampleConfig.from_file(output_path) == resolved_config


def test_config_model_writes_toml_with_generic_writer(tmp_path: Path) -> None:
    # Given: one validated config model and one TOML output file path.
    output_path = tmp_path / "config.toml"

    class ExampleConfig(ConfigModel):
        name: str
        count: int

    resolved_config = ExampleConfig(name="written", count=7)

    # When: the generic writer is used for a TOML file.
    resolved_config.to_file(output_path)

    # Then: the written file round-trips through the config loader.
    assert ExampleConfig.from_file(output_path) == resolved_config


def test_config_model_rejects_directory_path_with_generic_writer(tmp_path: Path) -> None:
    # Given: one directory path instead of one config output file path.
    output_path = tmp_path / "config-dir.json"
    output_path.mkdir()

    class ExampleConfig(ConfigModel):
        name: str

    resolved_config = ExampleConfig(name="json")

    # When: the generic writer is used.
    # Then: the directory path is rejected.
    with pytest.raises(ExtendingConfigPathError):
        resolved_config.to_file(output_path)


def test_config_model_rejects_directory_path_with_yaml_writer(tmp_path: Path) -> None:
    # Given: one directory path instead of one config output file path.
    output_path = tmp_path / "config-dir.json"
    output_path.mkdir()

    class ExampleConfig(ConfigModel):
        name: str

    resolved_config = ExampleConfig(name="json")

    # When: the YAML-specific writer is used.
    # Then: the directory path is rejected.
    with pytest.raises(ExtendingConfigPathError):
        resolved_config.to_yaml_file(output_path)


def test_config_model_rejects_directory_path_with_json_writer(tmp_path: Path) -> None:
    # Given: one directory path instead of one config output file path.
    output_path = tmp_path / "config-dir.json"
    output_path.mkdir()

    class ExampleConfig(ConfigModel):
        name: str

    resolved_config = ExampleConfig(name="json")

    # When: the JSON-specific writer is used.
    # Then: the directory path is rejected.
    with pytest.raises(ExtendingConfigPathError):
        resolved_config.to_json_file(output_path)


def test_config_model_rejects_directory_path_with_toml_writer(tmp_path: Path) -> None:
    # Given: one directory path instead of one config output file path.
    output_path = tmp_path / "config-dir.json"
    output_path.mkdir()

    class ExampleConfig(ConfigModel):
        name: str

    resolved_config = ExampleConfig(name="json")

    # When: the TOML-specific writer is used.
    # Then: the directory path is rejected.
    with pytest.raises(ExtendingConfigPathError):
        resolved_config.to_toml_file(output_path)


def test_config_model_rejects_unsupported_suffix_when_writing_generic_file(tmp_path: Path) -> None:
    # Given: one unsupported generic output file extension.
    output_path = tmp_path / "config.ini"

    class ExampleConfig(ConfigModel):
        name: str

    resolved_config = ExampleConfig(name="json")

    # When: the generic file writer is used.
    # Then: the writer rejects the unsupported file format.
    with pytest.raises(ExtendingConfigError):
        resolved_config.to_file(output_path)
