"""Spec models for pooled evaluation runs."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Self

from pydantic import Field, model_validator

from libs.config.config import ConfigModel
from libs.config.extending_config import ExtendingConfigModel
from libs.path.path import resolve_path
from libs.pydantic.types import AbsoluteFilePath, AbsolutePath, NonBlankString, NonBlankString255  # noqa: TC001


class NetworkEmulationSettings(ConfigModel):
    """One explicit network degradation profile."""

    download_throughput_kbps: int = Field(gt=0)
    latency_ms: int = Field(ge=0)
    upload_throughput_kbps: int = Field(gt=0)


class CpuEmulationSettings(ConfigModel):
    """One explicit CPU throttling profile."""

    rate: float = Field(gt=1.0)


class BenchmarkSettings(ConfigModel):
    """All runtime settings for one benchmark spec."""

    click_delay_pattern_ms: tuple[int, ...] = Field(min_length=1)
    cpu_emulation: CpuEmulationSettings | None = None
    iat_slug: NonBlankString255
    network_emulation: NetworkEmulationSettings | None = None
    plan_seed: int = Field(ge=0)
    run_count: int = Field(ge=1)


class BenchmarkSpec(ExtendingConfigModel):
    """One runnable leaf spec for evaluation benchmarks."""

    slug: NonBlankString255
    description: NonBlankString
    benchmark: BenchmarkSettings


class BenchmarkBatchJob(ConfigModel):
    """One explicit benchmark job in a batch file."""

    spec: Path
    output_dir: Path

    def resolve(self, base_directory: Path) -> ResolvedBenchmarkBatchJob:
        """Resolve one batch job against one batch-file directory.

        Args:
            base_directory: Directory used for relative path resolution.

        Returns:
            The resolved batch job.
        """
        return ResolvedBenchmarkBatchJob(
            spec=resolve_path(self.spec, base_directory),
            output_dir=resolve_path(self.output_dir, base_directory),
        )


class BenchmarkBatchSpec(ConfigModel):
    """Explicit batch input for multiple benchmark jobs."""

    jobs: list[BenchmarkBatchJob] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_jobs(self) -> Self:
        """Reject duplicate spec paths and output directories within one batch.

        Returns:
            The validated batch spec.
        """
        spec_paths = [job.spec for job in self.jobs]
        if len(spec_paths) != len(set(spec_paths)):
            raise ValueError("Each benchmark batch job must reference a unique spec path.")

        output_dirs = [job.output_dir for job in self.jobs]
        if len(output_dirs) != len(set(output_dirs)):
            raise ValueError("Each benchmark batch job must use its own output directory.")

        return self

    def resolve(self, base_directory: Path) -> ResolvedBenchmarkBatchSpec:
        """Resolve one batch spec against one batch-file directory.

        Args:
            base_directory: Directory used for relative path resolution.

        Returns:
            The resolved batch spec.
        """
        return ResolvedBenchmarkBatchSpec(
            jobs=[job.resolve(base_directory) for job in self.jobs],
        )


class ResolvedBenchmarkBatchJob(BenchmarkBatchJob):
    """One batch job whose paths have been resolved to absolute paths."""

    spec: AbsoluteFilePath
    output_dir: AbsolutePath


class ResolvedBenchmarkBatchSpec(BenchmarkBatchSpec):
    """One batch spec whose jobs have been resolved to absolute paths."""

    jobs: list[ResolvedBenchmarkBatchJob] = Field(min_length=1)
