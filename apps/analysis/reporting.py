"""CSV summaries for offline evaluation analysis."""

from __future__ import annotations

from collections import defaultdict
from shutil import copyfile
from statistics import mean, stdev
from typing import TYPE_CHECKING

from apps.analysis.file import read_csv, write_csv
from apps.analysis.models import (
    AnalysisConditionRow,
    AnalysisFullRow,
    AnalysisOverviewRow,
    ConditionClickDelayRow,
    TrialRow,
    WorkerRunRow,
)

if TYPE_CHECKING:
    from pathlib import Path


def write_report_artifacts(collection_dir: Path, output_dir: Path) -> None:
    """Write report-ready CSV tables.

    Args:
        collection_dir: Directory produced by the collect command.
        output_dir: Directory receiving summary CSVs.

    """
    required_files = (
        "manifest.yaml",
        "conditions.csv",
        "worker-runs.csv",
        "trials.csv",
    )
    missing_files = [file_name for file_name in required_files if not (collection_dir / file_name).is_file()]
    if missing_files:
        raise ValueError(f"Missing collection files in {collection_dir}: {', '.join(missing_files)}")

    conditions = read_csv(collection_dir / "conditions.csv", ConditionClickDelayRow)
    worker_runs = read_csv(collection_dir / "worker-runs.csv", WorkerRunRow)
    trials = read_csv(collection_dir / "trials.csv", TrialRow)
    click_delay_by_condition = {row.condition_slug: row.click_delay_ms for row in conditions}

    output_dir.mkdir(parents=True, exist_ok=True)
    copyfile(collection_dir / "manifest.yaml", output_dir / "manifest.yaml")
    write_csv(output_dir / "analysis-overview.csv", AnalysisOverviewRow, _build_overview_rows(worker_runs, trials))
    write_csv(
        output_dir / "analysis-conditions.csv",
        AnalysisConditionRow,
        _build_condition_summary_rows(worker_runs, trials, click_delay_by_condition),
    )
    write_csv(
        output_dir / "analysis-full.csv",
        AnalysisFullRow,
        _build_worker_summary_rows(worker_runs, trials, click_delay_by_condition),
    )


def _build_condition_summary_rows(
    worker_runs: list[WorkerRunRow],
    trials: list[TrialRow],
    click_delay_by_condition: dict[str, int],
) -> list[AnalysisConditionRow]:
    trials_by_condition: dict[str, list[TrialRow]] = defaultdict(list)
    worker_runs_by_condition: dict[str, list[WorkerRunRow]] = defaultdict(list)

    for worker_run in worker_runs:
        worker_runs_by_condition[worker_run.condition_slug].append(worker_run)
    for trial in trials:
        trials_by_condition[trial.condition_slug].append(trial)

    rows: list[AnalysisConditionRow] = []
    for condition_slug in sorted(click_delay_by_condition):
        condition_trials = trials_by_condition[condition_slug]
        condition_worker_runs = worker_runs_by_condition[condition_slug]
        session_count = _session_count(condition_trials)
        db_inside_window_count = _count_inside_window(condition_trials)
        rows.append(
            AnalysisConditionRow(
                condition_slug=condition_slug,
                click_delay_ms=click_delay_by_condition[condition_slug],
                worker_count=len(condition_worker_runs),
                run_duration=_format_run_duration(
                    sum(worker_run.run_duration_ms for worker_run in condition_worker_runs)
                ),
                session_count=session_count,
                trial_count=len(condition_trials),
                **_format_trial_metric_columns(condition_trials),
                db_inside_evaluator_window_count=db_inside_window_count,
                db_inside_evaluator_window_percent=_percent(db_inside_window_count, len(condition_trials)),
            )
        )

    return rows


def _build_worker_summary_rows(
    worker_runs: list[WorkerRunRow],
    trials: list[TrialRow],
    click_delay_by_condition: dict[str, int],
) -> list[AnalysisFullRow]:
    worker_runs_by_key = {(run.condition_slug, run.worker_id): run for run in worker_runs}
    trials_by_worker: dict[tuple[str, str], list[TrialRow]] = defaultdict(list)

    for trial in trials:
        key = (trial.condition_slug, trial.worker_id)
        trials_by_worker[key].append(trial)

    rows: list[AnalysisFullRow] = []
    for condition_slug, worker_id in sorted(worker_runs_by_key):
        worker_run = worker_runs_by_key[(condition_slug, worker_id)]
        worker_trials = trials_by_worker[(condition_slug, worker_id)]
        session_count = _session_count(worker_trials)
        db_inside_window_count = _count_inside_window(worker_trials)
        rows.append(
            AnalysisFullRow(
                condition_slug=condition_slug,
                worker_id=worker_id,
                click_delay_ms=click_delay_by_condition[condition_slug],
                platform_name=worker_run.platform_name,
                browser_name=worker_run.browser_name,
                browser_version=worker_run.browser_version,
                run_duration=_format_run_duration(worker_run.run_duration_ms),
                session_count=session_count,
                trial_count=len(worker_trials),
                **_format_trial_metric_columns(worker_trials),
                db_inside_evaluator_window_count=db_inside_window_count,
                db_inside_evaluator_window_percent=_percent(db_inside_window_count, len(worker_trials)),
            )
        )

    return rows


def _build_overview_rows(
    worker_runs: list[WorkerRunRow],
    trials: list[TrialRow],
) -> list[AnalysisOverviewRow]:
    return [
        AnalysisOverviewRow(
            condition_count=len({row.condition_slug for row in worker_runs}),
            worker_run_count=len(worker_runs),
            session_count=_session_count(trials),
            trial_count=len(trials),
            db_inside_evaluator_window_count=_count_inside_window(trials),
            db_inside_evaluator_window_percent=_percent(_count_inside_window(trials), len(trials)),
        )
    ]


def _session_count(trials: list[TrialRow]) -> int:
    return len({trial.session_key for trial in trials})


def _format_trial_metric_columns(trials: list[TrialRow]) -> dict[str, float | None]:
    client_latency_mean_ms, client_latency_sd_ms, client_latency_min_ms, client_latency_max_ms = _summarize_values(
        [trial.final_latency_ms for trial in trials]
    )
    (
        db_minus_evaluator_before_mean_ms,
        db_minus_evaluator_before_sd_ms,
        db_minus_evaluator_before_min_ms,
        db_minus_evaluator_before_max_ms,
    ) = _summarize_values([_compute_db_minus_evaluator_before(trial) for trial in trials])
    (
        evaluator_after_minus_db_mean_ms,
        evaluator_after_minus_db_sd_ms,
        evaluator_after_minus_db_min_ms,
        evaluator_after_minus_db_max_ms,
    ) = _summarize_values([_compute_evaluator_after_minus_db(trial) for trial in trials])
    dispatch_window_mean_ms, dispatch_window_sd_ms, dispatch_window_min_ms, dispatch_window_max_ms = _summarize_values(
        [_compute_dispatch_window(trial) for trial in trials]
    )
    return {
        "client_latency_mean_ms": client_latency_mean_ms,
        "client_latency_sd_ms": client_latency_sd_ms,
        "client_latency_min_ms": client_latency_min_ms,
        "client_latency_max_ms": client_latency_max_ms,
        "db_minus_evaluator_before_mean_ms": db_minus_evaluator_before_mean_ms,
        "db_minus_evaluator_before_sd_ms": db_minus_evaluator_before_sd_ms,
        "db_minus_evaluator_before_min_ms": db_minus_evaluator_before_min_ms,
        "db_minus_evaluator_before_max_ms": db_minus_evaluator_before_max_ms,
        "evaluator_after_minus_db_mean_ms": evaluator_after_minus_db_mean_ms,
        "evaluator_after_minus_db_sd_ms": evaluator_after_minus_db_sd_ms,
        "evaluator_after_minus_db_min_ms": evaluator_after_minus_db_min_ms,
        "evaluator_after_minus_db_max_ms": evaluator_after_minus_db_max_ms,
        "dispatch_window_mean_ms": dispatch_window_mean_ms,
        "dispatch_window_sd_ms": dispatch_window_sd_ms,
        "dispatch_window_min_ms": dispatch_window_min_ms,
        "dispatch_window_max_ms": dispatch_window_max_ms,
    }


def _count_inside_window(trials: list[TrialRow]) -> int:
    return len([trial for trial in trials if _trial_is_inside_window(trial)])


def _trial_is_inside_window(trial: TrialRow) -> bool:
    return trial.evaluator_latency_before_ms <= trial.final_latency_ms <= trial.evaluator_latency_after_ms


def _compute_db_minus_evaluator_before(trial: TrialRow) -> float:
    return trial.final_latency_ms - trial.evaluator_latency_before_ms


def _compute_evaluator_after_minus_db(trial: TrialRow) -> float:
    return trial.evaluator_latency_after_ms - trial.final_latency_ms


def _compute_dispatch_window(trial: TrialRow) -> float:
    return trial.evaluator_latency_after_ms - trial.evaluator_latency_before_ms


def _summarize_values(values: list[float]) -> tuple[float | None, float | None, float | None, float | None]:
    if not values:
        return None, None, None, None

    return (
        _round_or_none(mean(values)),
        _round_or_none(stdev(values) if len(values) > 1 else 0.0),
        _round_or_none(min(values)),
        _round_or_none(max(values)),
    )


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None

    return _round_or_none(numerator * 100.0 / denominator)


def _round_or_none(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def _format_run_duration(run_duration_ms: float) -> str:
    total_seconds = round(run_duration_ms / 1000.0)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"
