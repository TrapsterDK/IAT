"""Typed config models loaded from and written to YAML, JSON, or TOML files."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict

from libs.config.utils import ConfigFormat, detect_config_format, read_mapping_file, write_mapping_file

if TYPE_CHECKING:
    from pathlib import Path


class ConfigModel(BaseModel):
    """Typed config model loaded from one file without inheritance."""

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_file(cls, path: Path) -> Self:
        """Load and validate one config model from a supported file.

        Args:
            path: Config file path in YAML, JSON, or TOML format.

        Returns:
            The validated config model.
        """
        match detect_config_format(path):
            case ConfigFormat.YAML:
                return cls.from_yaml_file(path)
            case ConfigFormat.JSON:
                return cls.from_json_file(path)
            case ConfigFormat.TOML:
                return cls.from_toml_file(path)

    @classmethod
    def from_yaml_file(cls, path: Path) -> Self:
        """Load and validate one YAML-backed config model from disk.

        Args:
            path: YAML config file path.

        Returns:
            The validated config model.
        """
        return cls.model_validate(read_mapping_file(path, ConfigFormat.YAML))

    @classmethod
    def from_json_file(cls, path: Path) -> Self:
        """Load and validate one JSON-backed config model from disk.

        Args:
            path: JSON config file path.

        Returns:
            The validated config model.
        """
        return cls.model_validate(read_mapping_file(path, ConfigFormat.JSON))

    @classmethod
    def from_toml_file(cls, path: Path) -> Self:
        """Load and validate one TOML-backed config model from disk.

        Args:
            path: TOML config file path.

        Returns:
            The validated config model.
        """
        return cls.model_validate(read_mapping_file(path, ConfigFormat.TOML))

    def to_json_file(self, path: Path) -> None:
        """Write one config model to a stable JSON file on disk.

        Args:
            path: JSON file path to write.
        """
        write_mapping_file(path, self.model_dump(mode="json"), ConfigFormat.JSON)

    def to_yaml_file(self, path: Path) -> None:
        """Write one config model to a YAML file on disk.

        Args:
            path: YAML file path to write.
        """
        write_mapping_file(path, self.model_dump(mode="json"), ConfigFormat.YAML)

    def to_toml_file(self, path: Path) -> None:
        """Write one config model to a TOML file on disk.

        Args:
            path: TOML file path to write.
        """
        write_mapping_file(path, self.model_dump(mode="json"), ConfigFormat.TOML)

    def to_file(self, path: Path) -> None:
        """Write one config model to a supported file format on disk.

        Args:
            path: Config file path in YAML, JSON, or TOML format.
        """
        match detect_config_format(path):
            case ConfigFormat.YAML:
                self.to_yaml_file(path)
            case ConfigFormat.JSON:
                self.to_json_file(path)
            case ConfigFormat.TOML:
                self.to_toml_file(path)
