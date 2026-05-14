"""Runtime config for backend IAT resource discovery."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from libs.config.config import ConfigModel
from libs.pydantic.types import NonBlankString  # noqa: TC001

IAT_RESOURCES_CONFIG_PATH_ENV_VAR = "IAT_RESOURCES_CONFIG_PATH"


class IatResourcesSettings(ConfigModel):
    """Config that describes where IAT specs live and which ones are enabled."""

    iat_directory: Path = Path("resources/iats")
    enabled_iats: list[NonBlankString] = Field(default_factory=list)
