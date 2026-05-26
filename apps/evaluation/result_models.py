"""Saved result models for successful evaluation runs."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from pydantic import ConfigDict

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

    viewport_height_px: int
    viewport_width_px: int


class WorkerBenchmarkResult(ConfigModel):
    """Saved benchmark output for one worker run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    browser: WorkerBenchmarkBrowserResult
    run_duration_ms: int
    session_keys: list[str]


class ManifestJobRecord(ConfigModel):
    """Manifest entry pointing at one saved job result file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_file: Path


class BenchmarkManifest(ConfigModel):
    """Top-level saved manifest for one successful evaluation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark: BenchmarkSettings
    jobs: list[ManifestJobRecord]
