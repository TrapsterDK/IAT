"""Application settings and environment loading."""

from __future__ import annotations

import re
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parents[1]
RESOURCE_ROOT = PROJECT_ROOT / "resources"

SLUG_REGEX = re.compile(r"^[a-z0-9-]+$")


class LogLevel(StrEnum):
    """Supported application log levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SECRET_KEY: str = "dev-secret"
    DATABASE_URL: str = "sqlite:///app.sqlite3"
    ASSETS_DIR: Path = RESOURCE_ROOT
    DEFINITIONS_DIR: Path = RESOURCE_ROOT / "iats"
    DOWNLOAD_SOURCES_FILE: Path = RESOURCE_ROOT / "downloads" / "project-implicit.yaml"
    PROJECT_IMPLICIT_ASSETS_DIR: Path = RESOURCE_ROOT / "project-implicit"
    LOG_STDOUT: bool = True
    LOG_DIR: Path = PROJECT_ROOT / "logs"
    LOG_LEVEL: LogLevel = LogLevel.INFO
    UVICORN_HOST: str = "127.0.0.1"
    UVICORN_PORT: int = 8000
    UVICORN_RELOAD: bool = False
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


class DownloadSourceConfig(BaseModel):
    """One download source entry from the tracked manifest."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    link: str


class DownloadSourcesConfig(BaseModel):
    """Tracked Project Implicit download sources."""

    model_config = ConfigDict(extra="forbid")

    sources: list[DownloadSourceConfig]


class StimulusDefinitionConfig(BaseModel):
    """One stimulus entry from an IAT dataset YAML file."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    image: Path | None = None

    @model_validator(mode="after")
    def validate_content_fields(self) -> StimulusDefinitionConfig:
        """Require exactly one content payload per stimulus."""
        if (not self.text) == (self.image is None):
            raise ValueError("Each stimulus must define exactly one of text or image.")

        if self.image is not None:
            if self.image.is_absolute():
                raise ValueError("image must be a relative path beneath /assets.")

            resolved = (RESOURCE_ROOT / self.image).resolve()
            if RESOURCE_ROOT not in resolved.parents:
                raise ValueError("image paths must be located within the /resources directory.")

            if not resolved.is_file():
                raise ValueError("image paths must point to an existing file.")

        return self


class CategoryConfig(BaseModel):
    """One category inside an IAT dataset."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=SLUG_REGEX.pattern, min_length=1)
    label: str = Field(min_length=1)
    stimuli: list[StimulusDefinitionConfig] = Field(min_length=1)


class CategoryEntry(BaseModel):
    """One ordered category entry inside an IAT dataset."""

    model_config = ConfigDict(extra="forbid")

    category: tuple[CategoryConfig, CategoryConfig]


class IatDefinitionConfig(BaseModel):
    """Reusable IAT dataset configuration used to build runnable experiments."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=SLUG_REGEX.pattern, min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    categories: tuple[CategoryEntry, CategoryEntry]

    @model_validator(mode="after")
    def validate_slugs(self) -> IatDefinitionConfig:
        """Validate that the dataset slug and all category slugs are unique."""
        category_slugs = [category.slug for entry in self.categories for category in entry.category]
        if len(category_slugs) != len(set(category_slugs)):
            raise ValueError(f"IAT config {self.slug} defines duplicate category slugs.")

        return self


def load_download_source_configs(path: Path) -> DownloadSourcesConfig:
    """Load the tracked download source manifest."""
    with path.open(encoding="utf-8") as yaml_file:
        data = yaml.safe_load(yaml_file)
    return DownloadSourcesConfig.model_validate(data)


def load_iat_config(path: Path) -> IatDefinitionConfig:
    """Load one IAT dataset config from YAML."""
    with path.open(encoding="utf-8") as yaml_file:
        data = yaml.safe_load(yaml_file)
    return IatDefinitionConfig.model_validate(data)


def load_settings() -> Settings:
    """Load settings from the environment-backed BaseSettings model."""
    return Settings()  # ty:ignore[missing-argument]


@lru_cache(maxsize=1)
def get_config() -> Settings:
    """Load and cache process-wide settings on first access."""
    return load_settings()
