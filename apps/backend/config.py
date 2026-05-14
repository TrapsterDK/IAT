"""Runtime config for backend IAT resource discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from libs.config.config import ConfigModel

IAT_RESOURCES_CONFIG_PATH_ENV_VAR = "IAT_RESOURCES_CONFIG_PATH"


class IatResourcesSettings(ConfigModel):
    """Config that describes where IAT specs live and which ones are enabled."""

    iat_directory: Path = Path("resources/iats")
    enabled_iats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_settings(self) -> Self:
        """Validate one IAT resources config payload.

        Returns:
            The validated config instance.
        """
        for slug in self.enabled_iats:
            if not slug.strip():
                raise ValueError("Enabled IAT slugs must not be blank.")

        return self
