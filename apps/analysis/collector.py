"""Collection pipeline for report-oriented evaluation analysis files."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import bindparam, text

from apps.analysis.file import write_csv
from apps.analysis.models import (
    CollectionManifest,
    ConditionClickDelayRow,
    TrialRow,
    WorkerRunRow,
)
from apps.backend.database import create_session_factory, create_sqlite_engine
from apps.backend.models.session import SessionMode
from apps.evaluation.models import BenchmarkJobResult, BenchmarkManifest

if TYPE_CHECKING:
    from pathlib import Path


_SELECT_SESSION_ROWS = text(
    """
    SELECT
        session_key
    FROM iat_sessions
    WHERE session_mode = :session_mode AND session_key IN :session_keys
    ORDER BY session_key
    """
).bindparams(bindparam("session_keys", expanding=True))

_SELECT_BLOCK_ROWS = text(
    """
    SELECT
        s.session_key,
        p.block_index,
        p.is_practice
    FROM iat_sessions AS s
    JOIN iat_session_block_plans AS p ON p.session_id = s.id
    WHERE s.session_mode = :session_mode AND s.session_key IN :session_keys
    ORDER BY s.session_key, p.block_index
    """
).bindparams(bindparam("session_keys", expanding=True))

_SELECT_TRIAL_ROWS = text(
    """
    SELECT
        s.session_key,
        t.block_index,
        t.trial_index,
        CASE
            WHEN t.stimulus_image_path IS NULL THEN 'text'
            ELSE 'image'
        END AS stimulus_kind
    FROM iat_sessions AS s
    JOIN iat_session_trial_plans AS t ON t.session_id = s.id
    WHERE s.session_mode = :session_mode AND s.session_key IN :session_keys
    ORDER BY s.session_key, t.block_index, t.trial_index
    """
).bindparams(bindparam("session_keys", expanding=True))

_SELECT_EVENT_ROWS = text(
    """
    SELECT
        s.session_key,
        e.block_index,
        e.trial_index,
        e.event_index,
        e.elapsed_ms
    FROM iat_sessions AS s
    JOIN iat_session_trial_events AS e ON e.session_id = s.id
    WHERE s.session_mode = :session_mode AND s.session_key IN :session_keys
    ORDER BY s.session_key, e.block_index, e.trial_index, e.event_index
    """
).bindparams(bindparam("session_keys", expanding=True))


def collect_analysis_data(evaluation_results_root: Path, database_path: Path, output_dir: Path) -> None:
    """Collect report-ready rows from evaluation output and the backend database.

    Args:
        evaluation_results_root: Directory containing one or more evaluation manifests.
        database_path: SQLite database file containing persisted evaluation sessions.
        output_dir: Directory receiving the collected files.

    """
    if not evaluation_results_root.exists():
        raise ValueError(f"Evaluation results path does not exist: {evaluation_results_root}")
    if not evaluation_results_root.is_dir():
        raise ValueError(f"Evaluation results path must be a directory: {evaluation_results_root}")
    if not database_path.exists():
        raise ValueError(f"Database path does not exist: {database_path}")
    if not database_path.is_file():
        raise ValueError(f"Database path must be a file: {database_path}")

    loaded_worker_results = _load_worker_results(evaluation_results_root)
    session_rows, block_rows, trial_rows, event_rows = _load_database_rows(
        database_path,
        [
            session_key
            for _condition_slug, (_manifest, job_results) in loaded_worker_results.items()
            for job_result in job_results
            for session_key in job_result.result.session_keys
        ],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    CollectionManifest(
        database_sha256=_hash_file(database_path),
        conditions={
            condition_slug: manifest for condition_slug, (manifest, _job_results) in loaded_worker_results.items()
        },
    ).to_yaml_file(output_dir / "manifest.yaml")
    write_csv(output_dir / "conditions.csv", ConditionClickDelayRow, _generate_conditions(loaded_worker_results))
    write_csv(output_dir / "worker-runs.csv", WorkerRunRow, _generate_worker_runs(loaded_worker_results))
    write_csv(
        output_dir / "trials.csv",
        TrialRow,
        _generate_trials(session_rows, block_rows, trial_rows, event_rows, loaded_worker_results),
    )


def _load_worker_results(
    evaluation_results_root: Path,
) -> dict[str, tuple[BenchmarkManifest, list[BenchmarkJobResult]]]:
    manifest_paths = sorted(path for path in evaluation_results_root.rglob("manifest.yaml") if path.is_file())
    if not manifest_paths:
        raise ValueError(f"No evaluation manifests were found under: {evaluation_results_root}")

    loaded_worker_results: dict[str, tuple[BenchmarkManifest, list[BenchmarkJobResult]]] = {}
    for manifest_path in manifest_paths:
        condition_slug = manifest_path.parent.name
        if condition_slug in loaded_worker_results:
            raise ValueError(f"Duplicate analysis condition slug discovered: {condition_slug}")

        manifest = BenchmarkManifest.from_file(manifest_path)
        loaded_worker_results[condition_slug] = (
            manifest,
            [BenchmarkJobResult.from_file(manifest_path.parent / job.result_file) for job in manifest.jobs],
        )

    return loaded_worker_results


def _load_database_rows(
    database_path: Path,
    all_session_keys: list[str],
) -> tuple[
    list[tuple[str]],
    list[tuple[str, int, bool]],
    list[tuple[str, int, int, Literal["image", "text"]]],
    list[tuple[str, int, int, int, float]],
]:
    if not all_session_keys:
        return [], [], [], []

    engine = create_sqlite_engine(database_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as database_session:
            query_parameters = {"session_mode": SessionMode.EVALUATION.value, "session_keys": all_session_keys}
            return (
                cast("list", database_session.execute(_SELECT_SESSION_ROWS, query_parameters).all()),
                cast("list", database_session.execute(_SELECT_BLOCK_ROWS, query_parameters).all()),
                cast("list", database_session.execute(_SELECT_TRIAL_ROWS, query_parameters).all()),
                cast("list", database_session.execute(_SELECT_EVENT_ROWS, query_parameters).all()),
            )
    finally:
        engine.dispose()


def _generate_conditions(
    loaded_worker_results: dict[str, tuple[BenchmarkManifest, list[BenchmarkJobResult]]],
) -> list[ConditionClickDelayRow]:
    return [
        ConditionClickDelayRow(condition_slug=condition_slug, click_delay_ms=manifest.benchmark.click_delay_ms)
        for condition_slug, (manifest, _job_results) in loaded_worker_results.items()
    ]


def _generate_worker_runs(
    loaded_worker_results: dict[str, tuple[BenchmarkManifest, list[BenchmarkJobResult]]],
) -> list[WorkerRunRow]:
    return [
        WorkerRunRow(
            condition_slug=condition_slug,
            worker_id=job_result.worker.worker_id,
            browser_name=job_result.worker.browser_name,
            browser_version=job_result.worker.browser_version,
            platform_name=job_result.worker.platform_name,
            run_duration_ms=job_result.result.run_duration_ms,
        )
        for condition_slug, (_manifest, job_results) in loaded_worker_results.items()
        for job_result in job_results
    ]


def _hash_file(input_path: Path) -> str:
    return hashlib.sha256(input_path.read_bytes()).hexdigest()


def _generate_trials(  # noqa: PLR0912
    session_rows: list[tuple[str]],
    block_rows: list[tuple[str, int, bool]],
    trial_rows: list[tuple[str, int, int, Literal["image", "text"]]],
    event_rows: list[tuple[str, int, int, int, float]],
    loaded_worker_results: dict[str, tuple[BenchmarkManifest, list[BenchmarkJobResult]]],
) -> list[TrialRow]:
    session_keys = {session_key for session_key, *_ in session_rows}
    for session_key, *_ in trial_rows:
        if session_key not in session_keys:
            raise ValueError(f"Persisted trial rows reference missing evaluation sessions: {session_key}")

    trial_rows_by_session: defaultdict[str, list[tuple[int, int, Literal["image", "text"]]]] = defaultdict(list)
    for session_key, block_index, trial_index, stimulus_kind in trial_rows:
        trial_rows_by_session[session_key].append((block_index, trial_index, stimulus_kind))

    for session_key in trial_rows_by_session:
        trial_rows_by_session[session_key].sort()

    final_latency_by_trial_position: dict[tuple[str, int, int], float] = {}
    for session_key, block_index, trial_index, _event_index, elapsed_ms in event_rows:
        trial_key = (session_key, block_index, trial_index)
        if trial_key in final_latency_by_trial_position:
            raise ValueError(
                f"Persisted trial has more than one event row: {session_key}/block={block_index}/trial={trial_index}"
            )

        final_latency_by_trial_position[trial_key] = elapsed_ms

    for condition_slug, (_, job_results) in loaded_worker_results.items():
        for job_result in job_results:
            persisted_trial_rows = [
                (session_key, block_index, trial_index, stimulus_kind)
                for session_key in job_result.result.session_keys
                for block_index, trial_index, stimulus_kind in trial_rows_by_session[session_key]
            ]
            if len(persisted_trial_rows) != len(job_result.result.click_latencies_before_ms):
                raise ValueError(
                    "Evaluator latency count does not match persisted trial count: "
                    f"{condition_slug}/{job_result.worker.worker_id} "
                    f"persisted={len(persisted_trial_rows)} recorded={len(job_result.result.click_latencies_before_ms)}"
                )

            for session_key, block_index, trial_index, _stimulus_kind in persisted_trial_rows:
                if (session_key, block_index, trial_index) not in final_latency_by_trial_position:
                    raise ValueError(
                        "Missing final latency event for persisted trial: "
                        f"{condition_slug}/{job_result.worker.worker_id}/{session_key}/"
                        f"block={block_index}/trial={trial_index}"
                    )

    block_is_practice_by_position = {
        (session_key, block_index): is_practice for session_key, block_index, is_practice in block_rows
    }

    trials: list[TrialRow] = []
    for condition_slug, (_, job_results) in loaded_worker_results.items():
        for job_result in job_results:
            persisted_trial_rows = [
                (session_key, block_index, trial_index, stimulus_kind)
                for session_key in job_result.result.session_keys
                for block_index, trial_index, stimulus_kind in trial_rows_by_session[session_key]
            ]
            for (
                session_key,
                block_index,
                trial_index,
                stimulus_kind,
            ), evaluator_latency_before_ms, evaluator_latency_after_ms in zip(
                persisted_trial_rows,
                job_result.result.click_latencies_before_ms,
                job_result.result.click_latencies_after_ms,
                strict=True,
            ):
                trial_key = (session_key, block_index, trial_index)
                trials.append(
                    TrialRow(
                        condition_slug=condition_slug,
                        worker_id=job_result.worker.worker_id,
                        browser_name=job_result.worker.browser_name,
                        browser_version=job_result.worker.browser_version,
                        platform_name=job_result.worker.platform_name,
                        session_key=session_key,
                        block_index=block_index,
                        trial_index=trial_index,
                        is_practice=block_is_practice_by_position.get((session_key, block_index), False),
                        stimulus_kind=stimulus_kind,
                        final_latency_ms=final_latency_by_trial_position[trial_key],
                        evaluator_latency_before_ms=evaluator_latency_before_ms,
                        evaluator_latency_after_ms=evaluator_latency_after_ms,
                    )
                )

    return trials
