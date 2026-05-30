"""Saved result models for successful evaluation runs."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from pydantic import ConfigDict, Field, NonNegativeFloat, model_validator

from apps.evaluation.specs import BenchmarkSettings  # noqa: TC001
from libs.config.config import ConfigModel


class WorkerInfo(ConfigModel):
    """Persisted worker and device metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    worker_id: str
    browser_name: str | None = None
    browser_version: str | None = None
    platform_name: str | None = None


class WorkerBenchmarkResult(ConfigModel):
    """Saved benchmark output for one worker run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_duration_ms: float = Field(ge=0)
    session_keys: list[str] = Field(min_length=1)
    click_latencies_before_ms: list[NonNegativeFloat] = Field(default_factory=list)
    click_latencies_after_ms: list[NonNegativeFloat] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_matching_latency_lengths(self) -> WorkerBenchmarkResult:
        """Ensure evaluator latency arrays align one-to-one.

        Returns:
            The validated worker benchmark result.
        """
        if len(self.click_latencies_before_ms) != len(self.click_latencies_after_ms):
            raise ValueError(
                "Evaluator latency counts must match: "
                f"before={len(self.click_latencies_before_ms)} after={len(self.click_latencies_after_ms)}"
            )

        return self


class BenchmarkJobResult(ConfigModel):
    """Saved result for one successful worker benchmark run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    worker: WorkerInfo
    result: WorkerBenchmarkResult


class ManifestJobRecord(ConfigModel):
    """Manifest entry pointing at one saved job result file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_file: Path


class BenchmarkManifest(ConfigModel):
    """Top-level saved manifest for one successful evaluation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark: BenchmarkSettings
    jobs: list[ManifestJobRecord] = Field(min_length=1)
