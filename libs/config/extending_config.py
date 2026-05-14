"""Config file loaders with `extends` support across YAML, JSON, and TOML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Self

from libs.config.config import ConfigModel
from libs.config.exceptions import ExtendingConfigCycleError, ExtendingConfigError
from libs.config.utils import ConfigFormat, read_mapping_file


class ExtendingConfigModel(ConfigModel):
    """Typed config model that resolves file inheritance before validation."""

    extends_key: ClassVar[str] = "extends"

    @classmethod
    def from_yaml_file(cls, path: Path) -> Self:
        """Load and validate one YAML-backed config model from disk.

        Args:
            path: YAML config file path.

        Returns:
            The validated config model.
        """
        return cls.model_validate(_load_extending_mapping(path, cls.extends_key, ConfigFormat.YAML))

    @classmethod
    def from_json_file(cls, path: Path) -> Self:
        """Load and validate one JSON-backed config model from disk.

        Args:
            path: JSON config file path.

        Returns:
            The validated config model.
        """
        return cls.model_validate(_load_extending_mapping(path, cls.extends_key, ConfigFormat.JSON))

    @classmethod
    def from_toml_file(cls, path: Path) -> Self:
        """Load and validate one TOML-backed config model from disk.

        Args:
            path: TOML config file path.

        Returns:
            The validated config model.
        """
        return cls.model_validate(_load_extending_mapping(path, cls.extends_key, ConfigFormat.TOML))


def _load_extending_mapping(
    path: Path,
    extends_key: str,
    config_format: ConfigFormat | None = None,
) -> dict[str, Any]:
    """Resolve one config inheritance chain into a single mapping.

    Args:
        path: Config file path to load.
        extends_key: Mapping key used to declare inheritance.
        config_format: Optional explicit config format override.

    Returns:
        The merged config mapping.
    """
    return _load_extended_config_mapping(path, extends_key, set(), config_format)


def _load_extended_config_mapping(
    path: Path,
    extends_key: str,
    visited_paths: set[Path],
    config_format: ConfigFormat | None = None,
) -> dict[str, Any]:
    if path in visited_paths:
        raise ExtendingConfigCycleError(f"Cyclic config inheritance detected at: {path}")

    payload = read_mapping_file(path, config_format)
    extends_value = payload.pop(extends_key, None)
    if extends_value is None:
        return payload

    if not isinstance(extends_value, str) or not extends_value:
        raise ExtendingConfigError("The 'extends' value must be a non-empty string.")

    parent_path = Path(extends_value)
    if not parent_path.is_absolute():
        parent_path = path.parent / parent_path

    parent_payload = _load_extended_config_mapping(parent_path, extends_key, visited_paths | {path})
    return _merge_mappings(parent_payload, payload)


def _merge_mappings(base_payload: dict[str, Any], updating_payload: dict[str, Any]) -> dict[str, Any]:
    merged_payload = dict(base_payload)
    for key, updating_value in updating_payload.items():
        base_value = merged_payload.get(key)
        if isinstance(base_value, dict) and isinstance(updating_value, dict):
            merged_payload[key] = _merge_mappings(base_value, updating_value)
            continue

        merged_payload[key] = updating_value

    return merged_payload
