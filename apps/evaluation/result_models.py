"""Saved result models for successful evaluation runs."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from pydantic import ConfigDict, Field

from apps.evaluation.specs import BenchmarkSettings  # noqa: TC001
from libs.config.config import ConfigModel


class WorkerInfo(ConfigModel):
    """Persisted worker and device metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    worker_id: str
    browser_name: str | None = None
    browser_version: str | None = None
    platform_name: str | None = None


class BenchmarkJobResult(ConfigModel):
    """Saved result for one successful worker benchmark run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    worker: WorkerInfo
    result: WorkerBenchmarkResult


class WorkerBenchmarkBrowserResult(ConfigModel):
    """Saved browser snapshot for one worker run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    viewport_height_px: int = Field(ge=0)
    viewport_width_px: int = Field(ge=0)


class WorkerBenchmarkResult(ConfigModel):
    """Saved benchmark output for one worker run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    browser: WorkerBenchmarkBrowserResult
    run_duration_ms: int = Field(ge=0)
    session_keys: list[str] = Field(min_length=1)


class ManifestJobRecord(ConfigModel):
    """Manifest entry pointing at one saved job result file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_file: Path


class BenchmarkManifest(ConfigModel):
    """Top-level saved manifest for one successful evaluation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark: BenchmarkSettings
    jobs: list[ManifestJobRecord] = Field(min_length=1)
