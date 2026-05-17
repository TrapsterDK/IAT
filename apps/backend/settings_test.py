"""Tests for backend IAT resource settings loading and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.backend.settings import (
    IAT_RESOURCES_CONFIG_PATH_ENV_VAR,
    IatResourcesSettings,
    ResolvedIatResources,
    load_settings,
)
from libs.testing.io import write_yaml


def test_iat_resource_settings_load_from_yaml_file(tmp_path: Path) -> None:
    # Given: one YAML settings file that defines backend IAT resource paths.
    settings_path = tmp_path / "iat_spec.yaml"
    write_yaml(
        settings_path,
        {
            "host": "0.0.0.2",
            "port": 9000,
            "debug": False,
            "database_path": "instance/test.sqlite3",
            "iats": ["resources/iats/age-attitudes.yaml"],
        },
    )

    # When: the backend resource settings are loaded through the repo config library.
    settings = IatResourcesSettings.from_file(settings_path)

    # Then: the YAML values populate the typed settings model.
    assert settings.host == "0.0.0.2"
    assert settings.port == 9000
    assert settings.debug is False
    assert settings.database_path == Path("instance/test.sqlite3")
    assert settings.iats == (Path("resources/iats/age-attitudes.yaml"),)


def test_iat_resource_settings_reject_unknown_fields(tmp_path: Path) -> None:
    # Given: one backend settings file with one unsupported field.
    settings_path = tmp_path / "iat_spec.yaml"
    write_yaml(
        settings_path,
        {
            "extends": "./base.yaml",
        },
    )

    # When: the backend resource settings are loaded through the repo config library.
    # Then: validation rejects the unsupported field.
    with pytest.raises(ValidationError, match="extends"):
        IatResourcesSettings.from_file(settings_path)


def test_iat_resource_settings_reject_duplicate_iat_paths() -> None:
    # Given: one backend settings model with the same configured IAT path twice.

    # When: the settings model is validated.
    # Then: duplicate configured IAT paths are rejected.
    with pytest.raises(ValidationError, match="Collection items must be unique"):
        IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"), Path("resources/iats/sample-iat.yaml")))


def test_iat_resource_settings_reject_inverted_response_thresholds() -> None:
    # Given: one backend settings model whose anticipation threshold is not below the response timeout.

    # When: the settings model is validated.
    # Then: the inconsistent response timing configuration is rejected.
    with pytest.raises(ValidationError, match="anticipation threshold must be smaller than the response timeout"):
        IatResourcesSettings(anticipation_threshold_ms=1_000, response_timeout_ms=1_000, iats=())


def test_iat_resource_settings_are_frozen() -> None:
    # Given: one validated backend settings model.
    settings = IatResourcesSettings(iats=())

    # When: one field is reassigned after validation.
    # Then: the frozen settings model rejects mutation.
    with pytest.raises(ValidationError, match="Instance is frozen"):
        settings.debug = False


def test_iat_resource_settings_resolve_rejects_missing_iat_file(tmp_path: Path) -> None:
    # Given: one settings model that references one IAT file that does not exist.
    settings = IatResourcesSettings(iats=(Path("resources/iats/missing-iat.yaml"),))

    # When: the raw backend settings are resolved against the base directory.
    # Then: the missing IAT file is rejected by file-path validation.
    with pytest.raises(ValidationError, match="Path does not point to a file"):
        settings.resolve(tmp_path)


def test_iat_resource_settings_resolve_returns_absolute_existing_iat_paths(tmp_path: Path) -> None:
    # Given: one base directory that contains one configured IAT file.
    iat_path = tmp_path / "resources/iats/age-attitudes.yaml"
    write_yaml(iat_path, {"slug": "age-attitudes"})
    settings = IatResourcesSettings(
        host="0.0.0.2",
        port=9002,
        debug=False,
        iats=(Path("resources/iats/age-attitudes.yaml"),),
    )

    # When: the raw backend settings are resolved against the base directory.
    resolved_settings = settings.resolve(tmp_path)

    # Then: the resolved settings keep non-path values and resolve the configured file paths.
    assert resolved_settings.host == "0.0.0.2"
    assert resolved_settings.port == 9002
    assert resolved_settings.debug is False
    assert resolved_settings.database_path == (tmp_path / "instance/backend.sqlite3").resolve()
    assert resolved_settings.iats == (iat_path.resolve(),)


def test_iat_resource_settings_resolve_rejects_duplicate_resolved_iat_paths(tmp_path: Path) -> None:
    # Given: one settings model whose configured paths resolve to the same IAT file.
    iat_path = tmp_path / "resources/iats/age-attitudes.yaml"
    write_yaml(iat_path, {"slug": "age-attitudes"})
    settings = IatResourcesSettings(iats=(iat_path.resolve(), Path("resources/iats/age-attitudes.yaml")))

    # When: the raw backend settings are resolved against the base directory.
    # Then: duplicate resolved IAT paths are rejected.
    with pytest.raises(ValidationError, match="Collection items must be unique"):
        settings.resolve(tmp_path)


def test_resolved_iat_resources_reject_relative_iat_path(tmp_path: Path) -> None:
    # Given: one direct resolved-settings construction attempt with one relative IAT path.
    iat_path = tmp_path / "sample-iat.yaml"
    write_yaml(iat_path, {"slug": "sample-iat"})

    # When: the resolved settings model is validated.
    # Then: the relative IAT path is rejected by file validation before the absolute-path check.
    with pytest.raises(ValidationError, match="Path does not point to a file"):
        ResolvedIatResources(database_path=tmp_path / "instance/backend.sqlite3", iats=(Path("sample-iat.yaml"),))


def test_load_settings_uses_config_file_directory(tmp_path: Path) -> None:
    # Given: one config file with IAT paths relative to the config file location.
    config_directory = tmp_path / "config"
    resources_directory = config_directory / "bundled-resources"
    iat_path = resources_directory / "iats/sample-iat.yaml"
    write_yaml(iat_path, {"slug": "sample-iat"})
    config_path = config_directory / "iat-settings.yaml"
    write_yaml(
        config_path,
        {
            "host": "0.0.0.2",
            "port": 9001,
            "debug": False,
            "database_path": "instance/iat.sqlite3",
            "iats": ["bundled-resources/iats/sample-iat.yaml"],
        },
    )
    environment = {IAT_RESOURCES_CONFIG_PATH_ENV_VAR: str(config_path)}

    # When: the backend loads its resolved settings.
    resolved_settings = load_settings(environment)

    # Then: configured IAT file paths resolve relative to the config file.
    assert resolved_settings.host == "0.0.0.2"
    assert resolved_settings.port == 9001
    assert resolved_settings.debug is False
    assert resolved_settings.database_path == (config_directory / "instance/iat.sqlite3").resolve()
    assert resolved_settings.iats == (iat_path.resolve(),)


def test_load_settings_uses_workspace_default_without_config(tmp_path: Path) -> None:
    # Given: one Bazel workspace root with the default configured IAT files present.
    default_iat_paths = (
        tmp_path / "resources/iats/asian-black-pleasant-unpleasant.yaml",
        tmp_path / "resources/iats/asian-white-pleasant-unpleasant.yaml",
        tmp_path / "resources/iats/female-male-science-liberal-arts.yaml",
        tmp_path / "resources/iats/thin-fat-pleasant-unpleasant.yaml",
        tmp_path / "resources/iats/white-black-pleasant-unpleasant.yaml",
        tmp_path / "resources/iats/young-old-female-male.yaml",
        tmp_path / "resources/iats/young-old-pleasant-unpleasant.yaml",
    )
    for default_iat_path in default_iat_paths:
        write_yaml(default_iat_path, {"slug": "sample-iat"})
    environment = {"BUILD_WORKSPACE_DIRECTORY": str(tmp_path)}

    # When: the backend loads its resolved settings without one config override.
    resolved_settings = load_settings(environment)

    # Then: the default IAT paths resolve relative to the workspace root.
    assert resolved_settings.database_path == (tmp_path / "instance/backend.sqlite3").resolve()
    assert resolved_settings.iats[0] == default_iat_paths[0].resolve()


def test_load_settings_rejects_blank_config_path_env_var() -> None:
    # Given: one blank backend settings path in the process environment.
    environment = {IAT_RESOURCES_CONFIG_PATH_ENV_VAR: "   "}

    # When: the backend loads its resolved settings.
    # Then: the blank environment override is rejected.
    with pytest.raises(RuntimeError, match="must not be blank"):
        load_settings(environment)


def test_load_settings_requires_workspace_or_config() -> None:
    # Given: no config path and no Bazel workspace metadata.
    environment: dict[str, str] = {}

    # When: the backend loads its resolved settings.
    # Then: startup fails with one clear setup error.
    with pytest.raises(RuntimeError, match="No backend resource config was provided"):
        load_settings(environment)
