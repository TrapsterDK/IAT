"""Tests for backend IAT resource config loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from apps.backend.config import IatResourcesSettings


def _write_yaml(path: Path, payload: object) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_iat_resource_settings_load_from_yaml_file(tmp_path: Path) -> None:
    # Given: one YAML settings file that defines backend IAT resource paths.
    settings_path = tmp_path / "iat_spec.yaml"
    _write_yaml(
        settings_path,
        {
            "iat_directory": "resources/iats",
            "enabled_iats": ["age-attitudes"],
        },
    )

    # When: the backend resource settings are loaded through the repo config library.
    settings = IatResourcesSettings.from_file(settings_path)

    # Then: the YAML values populate the typed settings model.
    assert settings.iat_directory == Path("resources/iats")
    assert settings.enabled_iats == ["age-attitudes"]


def test_iat_resource_settings_default_paths_and_enabled_iats() -> None:
    # Given: one settings model instantiated without one file-backed override.

    # When: the backend resource settings are created directly in Python.
    settings = IatResourcesSettings()

    # Then: the model uses the default IAT path and enabled slug list.
    assert settings.iat_directory == Path("resources/iats")
    assert settings.enabled_iats == []


def test_iat_resource_settings_reject_unknown_fields(tmp_path: Path) -> None:
    # Given: one backend settings file with one unsupported field.
    settings_path = tmp_path / "iat_spec.yaml"
    _write_yaml(
        settings_path,
        {
            "iat_directory": "resources/iats",
            "extends": "./base.yaml",
        },
    )

    # When: the backend resource settings are loaded through the repo config library.
    # Then: validation rejects the unsupported field.
    with pytest.raises(ValidationError, match="extends"):
        IatResourcesSettings.from_file(settings_path)


def test_iat_resource_settings_reject_blank_enabled_iat_slug() -> None:
    # Given: one settings model with one blank enabled IAT slug.

    # When: the settings model is validated.
    # Then: validation rejects the blank slug.
    with pytest.raises(ValidationError, match="at least 1 character"):
        IatResourcesSettings(enabled_iats=["   "])
