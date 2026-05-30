"""Small row models for offline evaluation analysis."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from apps.evaluation.models import BenchmarkManifest  # noqa: TC001
from libs.config.config import ConfigModel


class WorkerRunRow(ConfigModel):
    """One benchmark run executed by one browser worker."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_slug: str
    worker_id: str
    browser_name: str | None
    browser_version: str | None
    platform_name: str | None
    run_duration_ms: float


class TrialRow(ConfigModel):
    """One completed trial with persisted and evaluator timing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_slug: str
    worker_id: str
    browser_name: str | None
    browser_version: str | None
    platform_name: str | None
    session_key: str
    block_index: int
    trial_index: int
    is_practice: bool
    stimulus_kind: Literal["image", "text"]
    final_latency_ms: float
    evaluator_latency_before_ms: float
    evaluator_latency_after_ms: float


class ConditionClickDelayRow(ConfigModel):
    """One condition slug paired with its click delay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_slug: str
    click_delay_ms: int


class CollectionManifest(ConfigModel):
    """Sanitized metadata about one collected dataset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    database_sha256: str
    conditions: dict[str, BenchmarkManifest]


class AnalysisOverviewRow(ConfigModel):
    """One-row aggregate summary for the full collected dataset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_count: int
    worker_run_count: int
    session_count: int
    trial_count: int
    db_inside_evaluator_window_count: int
    db_inside_evaluator_window_percent: float | None


class AnalysisConditionRow(ConfigModel):
    """Condition-level summary row for analysis reports."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_slug: str
    click_delay_ms: int
    worker_count: int
    session_count: int
    trial_count: int
    client_latency_mean_ms: float | None
    client_latency_sd_ms: float | None
    client_latency_min_ms: float | None
    client_latency_max_ms: float | None
    db_minus_evaluator_before_mean_ms: float | None
    db_minus_evaluator_before_sd_ms: float | None
    db_minus_evaluator_before_min_ms: float | None
    db_minus_evaluator_before_max_ms: float | None
    evaluator_after_minus_db_mean_ms: float | None
    evaluator_after_minus_db_sd_ms: float | None
    evaluator_after_minus_db_min_ms: float | None
    evaluator_after_minus_db_max_ms: float | None
    dispatch_window_mean_ms: float | None
    dispatch_window_sd_ms: float | None
    dispatch_window_min_ms: float | None
    dispatch_window_max_ms: float | None
    db_inside_evaluator_window_count: int
    db_inside_evaluator_window_percent: float | None


class AnalysisFullRow(ConfigModel):
    """Per-worker summary row for analysis reports."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_slug: str
    worker_id: str
    click_delay_ms: int
    platform_name: str | None
    browser_name: str | None
    browser_version: str | None
    session_count: int
    trial_count: int
    client_latency_mean_ms: float | None
    client_latency_sd_ms: float | None
    client_latency_min_ms: float | None
    client_latency_max_ms: float | None
    db_minus_evaluator_before_mean_ms: float | None
    db_minus_evaluator_before_sd_ms: float | None
    db_minus_evaluator_before_min_ms: float | None
    db_minus_evaluator_before_max_ms: float | None
    evaluator_after_minus_db_mean_ms: float | None
    evaluator_after_minus_db_sd_ms: float | None
    evaluator_after_minus_db_min_ms: float | None
    evaluator_after_minus_db_max_ms: float | None
    dispatch_window_mean_ms: float | None
    dispatch_window_sd_ms: float | None
    dispatch_window_min_ms: float | None
    dispatch_window_max_ms: float | None
    db_inside_evaluator_window_count: int
    db_inside_evaluator_window_percent: float | None
