"""Runtime settings for backend IAT resource and database discovery."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field, model_validator

from libs.bazel.workspace import get_build_workspace_directory
from libs.config.config import ConfigModel
from libs.path.path import resolve_path
from libs.pydantic.types import AbsoluteFilePath, AbsolutePath, NonBlankString, UniqueHashable  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Mapping

IAT_RESOURCES_CONFIG_PATH_ENV_VAR = "IAT_RESOURCES_CONFIG_PATH"


class SessionScoreInterpretationSettings(ConfigModel):
    """Magnitude thresholds used to convert one D-score into one headline."""

    little_to_no_association_upper_bound: float = Field(default=0.15, ge=0)
    slight_association_upper_bound: float = Field(default=0.35, gt=0)
    moderate_association_upper_bound: float = Field(default=0.65, gt=0)

    @model_validator(mode="after")
    def validate_thresholds(self) -> SessionScoreInterpretationSettings:
        """Ensure score interpretation thresholds increase strictly.

        Returns:
            The validated score interpretation settings instance.
        """
        if not (
            self.little_to_no_association_upper_bound
            < self.slight_association_upper_bound
            < self.moderate_association_upper_bound
        ):
            raise ValueError("The session score interpretation thresholds must increase strictly.")

        return self


class IatResourcesSettings(ConfigModel):
    """Config that describes where backend resources and the local database live."""

    host: NonBlankString = "127.0.0.1"
    port: int = Field(default=8000, ge=0, le=65535)
    debug: bool = True
    database_path: Path = Path("instance/backend.sqlite3")
    session_score_interpretation: SessionScoreInterpretationSettings = Field(
        default_factory=SessionScoreInterpretationSettings
    )
    iats: UniqueHashable[tuple[Path, ...]] = Field(
        default_factory=lambda: (
            Path("resources/iats/asian-black-pleasant-unpleasant.yaml"),
            Path("resources/iats/asian-white-pleasant-unpleasant.yaml"),
            Path("resources/iats/female-male-science-liberal-arts.yaml"),
            Path("resources/iats/thin-fat-pleasant-unpleasant.yaml"),
            Path("resources/iats/white-black-pleasant-unpleasant.yaml"),
            Path("resources/iats/young-old-female-male.yaml"),
            Path("resources/iats/young-old-pleasant-unpleasant.yaml"),
        )
    )

    def resolve(self, base_directory: Path) -> ResolvedIatResources:
        """Resolve configured resource paths against one base directory.

        Args:
            base_directory: Base directory used for relative path resolution.

        Returns:
            The resolved backend resource settings.
        """
        return ResolvedIatResources(
            host=self.host,
            port=self.port,
            debug=self.debug,
            database_path=resolve_path(self.database_path, base_directory),
            session_score_interpretation=self.session_score_interpretation,
            iats=tuple(resolve_path(iat_path, base_directory) for iat_path in self.iats),
        )


class ResolvedIatResources(IatResourcesSettings):
    """Resolved backend config with absolute paths for IAT files and the database."""

    database_path: AbsolutePath
    iats: UniqueHashable[tuple[AbsoluteFilePath, ...]]


def load_settings(environment: Mapping[str, str]) -> ResolvedIatResources:
    """Load resolved backend resource settings from config or Bazel defaults.

    Args:
        environment: Explicit process environment used to locate backend settings.

    Returns:
        The resolved backend resource settings.

    Raises:
        RuntimeError: The config path environment variable is blank.
        RuntimeError: No config path was provided and `BUILD_WORKSPACE_DIRECTORY` is unavailable.
    """
    config_path_value = environment.get(IAT_RESOURCES_CONFIG_PATH_ENV_VAR)
    if config_path_value is not None:
        stripped_config_path = config_path_value.strip()
        if not stripped_config_path:
            raise RuntimeError(f"Environment variable '{IAT_RESOURCES_CONFIG_PATH_ENV_VAR}' must not be blank.")

        config_path = Path(stripped_config_path).resolve()
        return IatResourcesSettings.from_file(config_path).resolve(config_path.parent)

    workspace_root = get_build_workspace_directory(environment)
    if workspace_root is None:
        raise RuntimeError(
            "No backend resource config was provided. Run through `bazel run` so "
            "BUILD_WORKSPACE_DIRECTORY is available, or set IAT_RESOURCES_CONFIG_PATH."
        )

    return IatResourcesSettings().resolve(workspace_root)
