"""Tests for config inheritance across YAML, JSON, and TOML."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel, ValidationError

from libs.config.exceptions import ExtendingConfigCycleError, ExtendingConfigError, ExtendingConfigPathError
from libs.config.extending_config import ExtendingConfigModel

if TYPE_CHECKING:
    from pathlib import Path


def test_extending_config_model_merges_cross_format_chains(tmp_path: Path) -> None:
    # Given: a TOML base config, a JSON middle config, and a YAML child config.
    toml_path = tmp_path / "base.toml"
    toml_path.write_text(
        'title = "base"\ntags = ["toml"]\n[nested]\nalpha = 1\nbeta = 2\n',
        encoding="utf-8",
    )
    json_path = tmp_path / "middle.json"
    json_path.write_text(
        json.dumps(
            {
                "extends": "./base.toml",
                "nested": {"beta": 5},
                "tags": ["json"],
            }
        ),
        encoding="utf-8",
    )
    yaml_path = tmp_path / "child.yaml"
    yaml_path.write_text(
        "extends: ./middle.json\ntitle: child\ntags:\n  - yaml\nnested:\n  gamma: 9\n",
        encoding="utf-8",
    )

    class ExampleNestedModel(BaseModel):
        alpha: int
        beta: int
        gamma: int = 0

    class ExampleConfig(ExtendingConfigModel):
        title: str
        nested: ExampleNestedModel
        tags: list[str]

    # When: the child config is loaded through the generic file entry point.
    resolved_config = ExampleConfig.from_file(yaml_path)

    # Then: nested mappings merge deeply while lists and scalars are overridden by the child.
    assert resolved_config.model_dump() == {
        "title": "child",
        "nested": {"alpha": 1, "beta": 5, "gamma": 9},
        "tags": ["yaml"],
    }


def test_extending_config_model_supports_yaml_explicit_loader(tmp_path: Path) -> None:
    # Given: one base YAML config and one child YAML config.
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "child.yaml"
    base_path.write_text("name: base\n", encoding="utf-8")
    child_path.write_text("extends: ./base.yaml\nname: child\n", encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the YAML-specific loader is used.
    resolved_config = ExampleNameConfig.from_yaml_file(child_path)

    # Then: the config validates successfully and resolves the parent chain.
    assert resolved_config.name == "child"


def test_extending_config_model_supports_json_explicit_loader(tmp_path: Path) -> None:
    # Given: one base JSON config and one child JSON config.
    base_path = tmp_path / "base.json"
    child_path = tmp_path / "child.json"
    base_path.write_text('{"name": "base"}', encoding="utf-8")
    child_path.write_text('{"extends": "./base.json", "name": "child"}', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the JSON-specific loader is used.
    resolved_config = ExampleNameConfig.from_json_file(child_path)

    # Then: the config validates successfully and resolves the parent chain.
    assert resolved_config.name == "child"


def test_extending_config_model_supports_toml_explicit_loader(tmp_path: Path) -> None:
    # Given: one base TOML config and one child TOML config.
    base_path = tmp_path / "base.toml"
    child_path = tmp_path / "child.toml"
    base_path.write_text('name = "base"\n', encoding="utf-8")
    child_path.write_text('extends = "./base.toml"\nname = "child"\n', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the TOML-specific loader is used.
    resolved_config = ExampleNameConfig.from_toml_file(child_path)

    # Then: the config validates successfully and resolves the parent chain.
    assert resolved_config.name == "child"


@pytest.mark.parametrize(
    ("loader_name", "base_file_name", "base_contents", "child_contents"),
    [
        pytest.param(
            "from_yaml_file",
            "base.yaml",
            "name: base\n",
            "extends: ./base.yaml\nname: child\n",
            id="yaml-explicit-format-override",
        ),
        pytest.param(
            "from_json_file",
            "base.json",
            '{"name": "base"}',
            '{"extends": "./base.json", "name": "child"}',
            id="json-explicit-format-override",
        ),
        pytest.param(
            "from_toml_file",
            "base.toml",
            'name = "base"\n',
            'extends = "./base.toml"\nname = "child"\n',
            id="toml-explicit-format-override",
        ),
    ],
)
def test_extending_config_model_explicit_loader_uses_format_override(
    tmp_path: Path,
    loader_name: str,
    base_file_name: str,
    base_contents: str,
    child_contents: str,
) -> None:
    # Given: one child config with an unsupported suffix and one parent config in the expected format.
    base_path = tmp_path / base_file_name
    child_path = tmp_path / "child.data"
    base_path.write_text(base_contents, encoding="utf-8")
    child_path.write_text(child_contents, encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the explicit loader is used.
    resolved_config = getattr(ExampleNameConfig, loader_name)(child_path)

    # Then: the explicit loader decodes the child file despite the unsupported suffix.
    assert resolved_config.name == "child"


def test_extending_config_model_allows_yaml_without_extends(tmp_path: Path) -> None:
    # Given: one standalone YAML config file with no `extends` key.
    config_path = tmp_path / "child.yaml"
    config_path.write_text("name: child\n", encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the generic file loader is used.
    resolved_config = ExampleNameConfig.from_file(config_path)

    # Then: the file loads normally without inheritance.
    assert resolved_config.name == "child"


def test_extending_config_model_allows_json_without_extends(tmp_path: Path) -> None:
    # Given: one standalone JSON config file with no `extends` key.
    config_path = tmp_path / "child.json"
    config_path.write_text('{"name": "child"}', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the generic file loader is used.
    resolved_config = ExampleNameConfig.from_file(config_path)

    # Then: the file loads normally without inheritance.
    assert resolved_config.name == "child"


def test_extending_config_model_allows_toml_without_extends(tmp_path: Path) -> None:
    # Given: one standalone TOML config file with no `extends` key.
    config_path = tmp_path / "child.toml"
    config_path.write_text('name = "child"\n', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the generic file loader is used.
    resolved_config = ExampleNameConfig.from_file(config_path)

    # Then: the file loads normally without inheritance.
    assert resolved_config.name == "child"


def test_extending_config_model_supports_absolute_parent_paths(tmp_path: Path) -> None:
    # Given: one child config that extends an absolute parent path.
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "child.yaml"
    base_path.write_text("name: base\ncount: 1\n", encoding="utf-8")
    child_path.write_text(f"extends: {base_path.resolve()}\nname: child\n", encoding="utf-8")

    class ExampleConfig(ExtendingConfigModel):
        name: str
        count: int

    # When: the child config is loaded.
    resolved_config = ExampleConfig.from_file(child_path)

    # Then: the absolute parent path is resolved and merged successfully.
    assert resolved_config.name == "child"
    assert resolved_config.count == 1


def test_extending_config_model_supports_custom_extends_key(tmp_path: Path) -> None:
    # Given: one extending config model that uses a custom inheritance key.
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "child.yaml"
    base_path.write_text("name: base\ncount: 1\n", encoding="utf-8")
    child_path.write_text("parent: ./base.yaml\nname: child\n", encoding="utf-8")

    class ExampleConfig(ExtendingConfigModel):
        extends_key = "parent"
        name: str
        count: int

    # When: the child config is loaded.
    resolved_config = ExampleConfig.from_file(child_path)

    # Then: the custom inheritance key is resolved and merged successfully.
    assert resolved_config.name == "child"
    assert resolved_config.count == 1


def test_extending_config_model_raises_for_cycles(tmp_path: Path) -> None:
    # Given: two configs that extend each other.
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    first_path.write_text("extends: ./second.yaml\nname: first\n", encoding="utf-8")
    second_path.write_text("extends: ./first.yaml\nname: second\n", encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the inheritance chain is loaded.
    # Then: the loader reports the inheritance cycle.
    with pytest.raises(ExtendingConfigCycleError):
        ExampleNameConfig.from_file(first_path)


def test_extending_config_model_raises_for_missing_parent(tmp_path: Path) -> None:
    # Given: a config that extends a missing parent file.
    child_path = tmp_path / "child.yaml"
    child_path.write_text("extends: ./missing.yaml\nname: child\n", encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the inheritance chain is loaded.
    # Then: the loader reports the missing parent path.
    with pytest.raises(ExtendingConfigPathError):
        ExampleNameConfig.from_file(child_path)


def test_extending_config_model_rejects_empty_yaml_extends_value(tmp_path: Path) -> None:
    # Given: one YAML config file with an empty `extends` value.
    child_path = tmp_path / "child.yaml"
    child_path.write_text("extends: ''\nname: child\n", encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the invalid `extends` value.
    with pytest.raises(ExtendingConfigError, match="extends"):
        ExampleNameConfig.from_file(child_path)


def test_extending_config_model_rejects_empty_json_extends_value(tmp_path: Path) -> None:
    # Given: one JSON config file with an empty `extends` value.
    child_path = tmp_path / "child.json"
    child_path.write_text('{"extends": "", "name": "child"}', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the invalid `extends` value.
    with pytest.raises(ExtendingConfigError, match="extends"):
        ExampleNameConfig.from_file(child_path)


def test_extending_config_model_rejects_empty_toml_extends_value(tmp_path: Path) -> None:
    # Given: one TOML config file with an empty `extends` value.
    child_path = tmp_path / "child.toml"
    child_path.write_text('extends = ""\nname = "child"\n', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the invalid `extends` value.
    with pytest.raises(ExtendingConfigError, match="extends"):
        ExampleNameConfig.from_file(child_path)


def test_extending_config_model_rejects_non_string_yaml_extends_value(tmp_path: Path) -> None:
    # Given: one YAML config file with a non-string `extends` value.
    child_path = tmp_path / "child.yaml"
    child_path.write_text("extends: 1\nname: child\n", encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the invalid `extends` value.
    with pytest.raises(ExtendingConfigError, match="extends"):
        ExampleNameConfig.from_file(child_path)


def test_extending_config_model_rejects_non_string_json_extends_value(tmp_path: Path) -> None:
    # Given: one JSON config file with a non-string `extends` value.
    child_path = tmp_path / "child.json"
    child_path.write_text('{"extends": 1, "name": "child"}', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the invalid `extends` value.
    with pytest.raises(ExtendingConfigError, match="extends"):
        ExampleNameConfig.from_file(child_path)


def test_extending_config_model_rejects_non_string_toml_extends_value(tmp_path: Path) -> None:
    # Given: one TOML config file with a non-string `extends` value.
    child_path = tmp_path / "child.toml"
    child_path.write_text('extends = 1\nname = "child"\n', encoding="utf-8")

    class ExampleNameConfig(ExtendingConfigModel):
        name: str

    # When: the file loader is used.
    # Then: the loader rejects the invalid `extends` value.
    with pytest.raises(ExtendingConfigError, match="extends"):
        ExampleNameConfig.from_file(child_path)


def test_extending_config_model_validation_runs_after_inheritance_resolution(tmp_path: Path) -> None:
    # Given: one valid base config and one child config that still fails schema validation after merging.
    base_path = tmp_path / "base.yaml"
    base_path.write_text("name: base\ncount: 1\n", encoding="utf-8")
    child_path = tmp_path / "child.yaml"
    child_path.write_text("extends: ./base.yaml\n", encoding="utf-8")

    class ExampleConfig(ExtendingConfigModel):
        name: str
        count: int
        label: str

    # When: the extending file loader is used.
    # Then: validation still applies to the merged payload.
    with pytest.raises(ValidationError):
        ExampleConfig.from_file(child_path)
