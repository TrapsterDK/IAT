"""CLI entrypoint for running evaluation benchmarks."""

from __future__ import annotations

import os
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from yarl import URL

from apps.evaluation.grid import discover_grid_workers
from apps.evaluation.result_models import BenchmarkJobResult, BenchmarkManifest, ManifestJobRecord
from apps.evaluation.runner import run_benchmark_job
from apps.evaluation.specs import BenchmarkBatchSpec, BenchmarkSpec
from libs.bazel.workspace import get_build_working_directory
from libs.path.path import resolve_path

if TYPE_CHECKING:
    from apps.evaluation.grid import GridWorker


app = typer.Typer(no_args_is_help=True)
DEFAULT_GRID_URL = URL("http://127.0.0.1:4444")


def _working_directory() -> Path:
    return get_build_working_directory(os.environ) or Path.cwd()


def _parse_url(value: str) -> URL:
    return URL(value)


def _time_log() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # noqa: DTZ005


def _run_specs(
    resolved_jobs: list[tuple[BenchmarkSpec, Path]],
    app_url: URL,
    grid_url: URL,
) -> None:
    """Run one or more resolved benchmark specs.

    Args:
        resolved_jobs: Resolved benchmark spec and output-directory pairs.
        app_url: Participant app URL opened in the automated browser.
        grid_url: Selenium Grid router URL.
    """
    workers = discover_grid_workers(grid_url)
    if not workers:
        raise ValueError("Evaluation runs require at least one discovered worker.")

    typer.echo("workers: \n" + "\n".join(f" - {worker.worker_id} {worker.browser_name}" for worker in workers))

    failed_job_count = 0

    for _, resolved_output_dir in resolved_jobs:
        resolved_output_dir.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=len(workers)) as executor:
        for benchmark_spec, resolved_output_dir in resolved_jobs:
            futures: dict[Future[BenchmarkJobResult], GridWorker] = {
                executor.submit(run_benchmark_job, grid_url, worker, benchmark_spec.benchmark, app_url): worker
                for worker in workers
            }

            completed_worker_ids = []
            for future in as_completed(futures):
                worker = futures[future]
                try:
                    payload = future.result()
                except Exception as error:  # noqa: BLE001
                    failed_job_count += 1
                    typer.echo(
                        f"{_time_log()} {benchmark_spec.slug}/{worker.worker_id}: benchmark failed: {error}", err=True
                    )
                else:
                    payload.to_yaml_file(resolved_output_dir / f"{worker.worker_id}.yaml")
                    completed_worker_ids.append(worker.worker_id)

            completed_worker_ids = sorted(completed_worker_ids)
            if not completed_worker_ids:
                typer.echo(
                    f"{_time_log()} {benchmark_spec.slug}: no benchmark jobs completed successfully; skipped manifest.",
                    err=True,
                )
                continue

            manifest = BenchmarkManifest(
                benchmark=benchmark_spec.benchmark,
                jobs=[ManifestJobRecord(result_file=Path(f"{worker_id}.yaml")) for worker_id in completed_worker_ids],
            )
            manifest.to_yaml_file(resolved_output_dir / "manifest.yaml")
            typer.echo(f"{_time_log()} {benchmark_spec.slug}: wrote evaluation results to {resolved_output_dir}")

    if failed_job_count > 0:
        typer.echo(f"{_time_log()} {failed_job_count} benchmark job(s) failed. See error logs for details.", err=True)
        raise typer.Exit(code=1)


@app.command("spec")
def spec_command(
    spec_path: Annotated[Path, typer.Argument(help="Leaf benchmark spec file.")],
    app_url: Annotated[URL, typer.Option("--app-url", parser=_parse_url)],
    output_dir: Annotated[Path, typer.Option("--output-dir")],
    grid_url: Annotated[URL, typer.Option("--grid-url", parser=_parse_url)] = DEFAULT_GRID_URL,
) -> None:
    """Run one benchmark resource spec on every discovered Grid worker.

    Args:
        spec_path: Leaf benchmark spec file.
        app_url: Participant app URL opened in the automated browser.
        output_dir: Output directory where this spec writes its manifest and worker result YAML files.
        grid_url: Selenium Grid router URL. Defaults to the local Grid router.
    """
    working_directory = _working_directory()
    resolved_spec_path = resolve_path(spec_path.expanduser(), working_directory)
    benchmark_spec = BenchmarkSpec.from_file(resolved_spec_path)
    _run_specs(
        [
            (
                benchmark_spec,
                resolve_path(output_dir.expanduser(), working_directory),
            )
        ],
        app_url,
        grid_url,
    )


@app.command("batch")
def batch_command(
    batch_path: Annotated[Path, typer.Argument(help="Batch file with explicit benchmark spec jobs.")],
    app_url: Annotated[URL, typer.Option("--app-url", parser=_parse_url)],
    grid_url: Annotated[URL, typer.Option("--grid-url", parser=_parse_url)] = DEFAULT_GRID_URL,
) -> None:
    """Run one benchmark batch file on every discovered Grid worker.

    Args:
        batch_path: Batch file with explicit benchmark spec jobs.
        app_url: Participant app URL opened in the automated browser.
        grid_url: Selenium Grid router URL. Defaults to the local Grid router.
    """
    resolved_batch_path = resolve_path(batch_path.expanduser(), _working_directory())
    benchmark_batch = BenchmarkBatchSpec.from_file(resolved_batch_path).resolve(resolved_batch_path.parent)
    _run_specs(
        [
            (
                BenchmarkSpec.from_file(job.spec),
                job.output_dir,
            )
            for job in benchmark_batch.jobs
        ],
        app_url,
        grid_url,
    )


if __name__ == "__main__":
    app()
