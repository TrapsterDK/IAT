"""Executable entrypoint for the offline analysis CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from apps.analysis.collector import collect_analysis_data
from apps.analysis.reporting import write_report_artifacts
from libs.bazel.workspace import get_build_working_directory
from libs.path.path import resolve_path

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
DEFAULT_DATABASE_PATH = Path("instance/backend.sqlite3")
DEFAULT_EVALUATION_RESULTS_DIR = Path("resources/evaluation-results")


def _working_directory() -> Path:
    return get_build_working_directory(os.environ) or Path.cwd()


@app.command("collect", help="Collect report-ready analysis files from evaluation output.")
def collect_command(
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Output directory for the collected CSV files.")],
    evaluation_results_dir: Annotated[
        Path,
        typer.Option("--evaluation-results-dir", help="Evaluation results root directory."),
    ] = DEFAULT_EVALUATION_RESULTS_DIR,
    database_path: Annotated[
        Path,
        typer.Option("--database-path", help="SQLite database file used by the backend."),
    ] = DEFAULT_DATABASE_PATH,
) -> None:
    """Collect report-ready analysis files from evaluation output and the database.

    Args:
        output_dir: Output directory for the collected analysis files.
        evaluation_results_dir: Evaluation results root directory.
        database_path: SQLite database file used by the backend.
    """
    working_directory = _working_directory()
    resolved_output_dir = resolve_path(output_dir.expanduser(), working_directory)
    resolved_evaluation_results_dir = resolve_path(evaluation_results_dir.expanduser(), working_directory)
    resolved_database_path = resolve_path(database_path.expanduser(), working_directory)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    collect_analysis_data(
        resolved_evaluation_results_dir,
        resolved_database_path,
        resolved_output_dir,
    )
    typer.echo(f"Collection outputs written to: {resolved_output_dir}")


@app.command("report", help="Write summary CSVs from collected analysis files.")
def report_command(
    collection_dir: Annotated[
        Path,
        typer.Option("--collection-dir", help="Directory produced by the collect command."),
    ],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Output directory for the report artifacts.")],
) -> None:
    """Write summary CSV files from collected analysis files.

    Args:
        collection_dir: Directory produced by the collect command.
        output_dir: Output directory for the report artifacts.
    """
    working_directory = _working_directory()
    resolved_collection_dir = resolve_path(collection_dir.expanduser(), working_directory)
    resolved_output_dir = resolve_path(output_dir.expanduser(), working_directory)

    write_report_artifacts(resolved_collection_dir, resolved_output_dir)
    typer.echo(f"Report outputs written to: {resolved_output_dir}")


if __name__ == "__main__":
    app()
