"""Shared utilities for file-backed config models."""

from __future__ import annotations

import json
import tomllib
from enum import Enum
from typing import TYPE_CHECKING, Any

import tomli_w
import yaml

from libs.config.exceptions import ExtendingConfigError, ExtendingConfigPathError

if TYPE_CHECKING:
    from pathlib import Path


class ConfigFormat(Enum):
    """Supported file formats for typed config models."""

    YAML = "yaml"
    JSON = "json"
    TOML = "toml"


def read_mapping_file(path: Path, config_format: ConfigFormat | None = None) -> dict[str, Any]:
    """Read one supported config file into a validated string-key mapping.

    Args:
        path: Config file path to read.
        config_format: Optional explicit config format override.

    Returns:
        The decoded config mapping.
    """
    try:
        match config_format or detect_config_format(path):
            case ConfigFormat.YAML:
                loaded_data = yaml.safe_load(path.read_text(encoding="utf-8"))
            case ConfigFormat.JSON:
                loaded_data = json.loads(path.read_text(encoding="utf-8"))
            case ConfigFormat.TOML:
                with path.open("rb") as file_handle:
                    loaded_data = tomllib.load(file_handle)
    except FileNotFoundError as error:
        raise ExtendingConfigPathError(f"Config file does not exist: {path}") from error
    except IsADirectoryError as error:
        raise ExtendingConfigPathError(f"Config path is not a file: {path}") from error

    if loaded_data is None:
        return {}

    if not isinstance(loaded_data, dict):
        raise ExtendingConfigError(f"Config files must decode to a mapping: {path}")

    for key in loaded_data:
        if not isinstance(key, str):
            raise ExtendingConfigError(f"Config mapping keys must be strings: {path}")

    return loaded_data


def write_mapping_file(path: Path, payload: dict[str, Any], config_format: ConfigFormat | None = None) -> None:
    """Write one supported config mapping to disk.

    Args:
        path: Config file path to write.
        payload: Decoded config mapping to serialize.
        config_format: Optional explicit config format override.
    """
    try:
        match config_format or detect_config_format(path):
            case ConfigFormat.YAML:
                serialized_payload = yaml.safe_dump(payload, sort_keys=False)
            case ConfigFormat.JSON:
                serialized_payload = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            case ConfigFormat.TOML:
                serialized_payload = tomli_w.dumps(payload)
    except TypeError as error:
        raise ExtendingConfigError(f"Config file contains values that cannot be serialized: {path}") from error

    try:
        path.write_text(serialized_payload, encoding="utf-8")
    except FileNotFoundError as error:
        raise ExtendingConfigPathError(f"Config parent directory does not exist: {path.parent}") from error
    except IsADirectoryError as error:
        raise ExtendingConfigPathError(f"Config path is not a file: {path}") from error


def detect_config_format(path: Path) -> ConfigFormat:
    """Detect one supported config format from a path suffix.

    Args:
        path: Config file path.

    Returns:
        The detected config format.
    """
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return ConfigFormat.YAML
    if suffix == ".json":
        return ConfigFormat.JSON
    if suffix == ".toml":
        return ConfigFormat.TOML

    raise ExtendingConfigError(
        f"Unsupported config file format for '{path}'. Expected one of: .json, .toml, .yaml, .yml"
    )
