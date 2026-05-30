"""Helpers for writing evaluation result manifests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from apps.evaluation.models import BenchmarkManifest, ManifestJobRecord

if TYPE_CHECKING:
    from apps.evaluation.specs import BenchmarkSpec

MANIFEST_FILE_NAME = "manifest.yaml"


def write_merged_manifest(
    resolved_output_dir: Path,
    benchmark_spec: BenchmarkSpec,
    completed_worker_ids: list[str],
) -> None:
    """Write one manifest while preserving compatible existing worker results.

    Args:
        resolved_output_dir: Directory containing worker result YAML files and the manifest.
        benchmark_spec: Benchmark spec used for the current run.
        completed_worker_ids: Worker IDs completed by the current run.
    """
    manifest_path = resolved_output_dir / MANIFEST_FILE_NAME
    existing_jobs = []
    if manifest_path.exists():
        existing_manifest = BenchmarkManifest.from_yaml_file(manifest_path)
        if existing_manifest.benchmark != benchmark_spec.benchmark:
            raise ValueError(
                f"Existing evaluation manifest at {manifest_path} was created for a different benchmark. "
                "Use a different output directory or rerun the same benchmark spec."
            )
        existing_jobs = existing_manifest.jobs

    jobs_by_result_file = {job.result_file: job for job in existing_jobs}
    for worker_id in completed_worker_ids:
        result_file = Path(f"{worker_id}.yaml")
        jobs_by_result_file[result_file] = ManifestJobRecord(result_file=result_file)

    manifest = BenchmarkManifest(
        benchmark=benchmark_spec.benchmark,
        jobs=sorted(jobs_by_result_file.values(), key=lambda job: job.result_file.as_posix()),
    )
    manifest.to_yaml_file(manifest_path)
