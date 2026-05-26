"""Tests for evaluation spec loading and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from apps.evaluation.specs import (
    BenchmarkBatchSpec,
    BenchmarkSettings,
    BenchmarkSpec,
    CpuEmulationSettings,
    NetworkEmulationSettings,
)
from libs.testing.io import write_yaml

if TYPE_CHECKING:
    from pathlib import Path


def test_benchmark_settings_accept_one_minimal_baseline_definition() -> None:
    # Given: one baseline benchmark settings block with one IAT slug, one run count, and one plan seed.
    benchmark_settings = BenchmarkSettings(
        click_delay_ms=700,
        iat_slug="sample-iat",
        plan_seed=123,
        run_count=5,
    )

    # When: the settings are inspected after validation.
    # Then: the core benchmark inputs are preserved.
    assert benchmark_settings.click_delay_ms == 700
    assert benchmark_settings.cpu_emulation is None
    assert benchmark_settings.iat_slug == "sample-iat"
    assert benchmark_settings.network_emulation is None
    assert benchmark_settings.run_count == 5
    assert benchmark_settings.plan_seed == 123
    assert benchmark_settings.model_dump(mode="json") == {
        "click_delay_ms": 700,
        "cpu_emulation": None,
        "iat_slug": "sample-iat",
        "network_emulation": None,
        "plan_seed": 123,
        "run_count": 5,
    }


def test_benchmark_settings_accept_one_cpu_throttling_definition() -> None:
    # Given: one CPU-throttling settings block with one explicit throttling rate.
    benchmark_settings = BenchmarkSettings(
        click_delay_ms=700,
        cpu_emulation=CpuEmulationSettings(rate=2.0),
        iat_slug="sample-iat",
        plan_seed=123,
        run_count=5,
    )

    # When: the settings are inspected after validation.
    # Then: the throttling metadata is preserved in the benchmark payload.
    assert benchmark_settings.cpu_emulation is not None
    assert benchmark_settings.cpu_emulation.rate == 2.0
    assert benchmark_settings.model_dump(mode="json")["cpu_emulation"] == {"rate": 2.0}


def test_benchmark_settings_accept_one_network_degradation_definition() -> None:
    # Given: one network-degradation settings block with one explicit network-emulation profile.
    benchmark_settings = BenchmarkSettings(
        click_delay_ms=700,
        iat_slug="sample-iat",
        network_emulation=NetworkEmulationSettings(
            download_throughput_kbps=1600,
            latency_ms=150,
            upload_throughput_kbps=750,
        ),
        plan_seed=123,
        run_count=5,
    )

    # When: the settings are inspected after validation.
    # Then: the network metadata is preserved in the benchmark payload.
    assert benchmark_settings.network_emulation is not None
    assert benchmark_settings.model_dump(mode="json")["network_emulation"] == {
        "download_throughput_kbps": 1600,
        "latency_ms": 150,
        "upload_throughput_kbps": 750,
    }


def test_benchmark_settings_accept_combined_cpu_and_network_definition() -> None:
    # Given: one benchmark settings block with both CPU throttling and network emulation.
    benchmark_settings = BenchmarkSettings(
        click_delay_ms=700,
        cpu_emulation=CpuEmulationSettings(rate=2.0),
        iat_slug="sample-iat",
        network_emulation=NetworkEmulationSettings(
            download_throughput_kbps=1600,
            latency_ms=150,
            upload_throughput_kbps=750,
        ),
        plan_seed=123,
        run_count=5,
    )

    # When: the settings are inspected after validation.
    # Then: both environment modifiers are preserved together.
    assert benchmark_settings.cpu_emulation is not None
    assert benchmark_settings.cpu_emulation.rate == 2.0
    assert benchmark_settings.network_emulation is not None


def test_benchmark_settings_reject_zero_run_count() -> None:
    # Given: one benchmark settings block with one invalid zero run count.

    # When: the settings are validated.
    # Then: validation rejects the non-positive run count.
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        BenchmarkSettings(
            click_delay_ms=300,
            iat_slug="sample-iat",
            plan_seed=123,
            run_count=0,
        )


def test_benchmark_spec_requires_one_click_delay_value(tmp_path: Path) -> None:
    # Given: one benchmark spec file with one invalid negative click delay.
    spec_path = tmp_path / "benchmark.yaml"
    write_yaml(
        spec_path,
        {
            "slug": "baseline-text-text",
            "description": "Baseline benchmark.",
            "benchmark": {
                "click_delay_ms": -1,
                "iat_slug": "sample-iat",
                "plan_seed": 123,
                "run_count": 5,
            },
        },
    )

    # When: the benchmark spec is validated.
    # Then: validation rejects the negative click delay.
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        BenchmarkSpec.from_file(spec_path)


def test_benchmark_spec_merges_extended_yaml_files(tmp_path: Path) -> None:
    # Given: one base benchmark spec and one child spec that overrides the benchmark settings.
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "baseline-text-text.yaml"
    write_yaml(
        base_path,
        {
            "benchmark": {
                "click_delay_ms": 700,
                "iat_slug": "base-iat",
                "plan_seed": 123,
                "run_count": 7,
            },
        },
    )
    write_yaml(
        child_path,
        {
            "extends": "./base.yaml",
            "slug": "baseline-text-text",
            "description": "Baseline benchmark.",
            "benchmark": {
                "iat_slug": "sample-iat",
                "plan_seed": 123,
            },
        },
    )

    # When: the child benchmark spec is loaded.
    benchmark_spec = BenchmarkSpec.from_file(child_path)

    # Then: inheritance merges the benchmark settings into one runnable spec.
    assert benchmark_spec.slug == "baseline-text-text"
    assert benchmark_spec.benchmark.click_delay_ms == 700
    assert benchmark_spec.benchmark.iat_slug == "sample-iat"
    assert benchmark_spec.benchmark.run_count == 7
    assert benchmark_spec.benchmark.plan_seed == 123


def test_benchmark_batch_spec_rejects_duplicate_output_directories(tmp_path: Path) -> None:
    # Given: one batch file with two jobs that use the same output directory.
    batch_path = tmp_path / "duplicate-output-dir.yaml"
    write_yaml(
        batch_path,
        {
            "jobs": [
                {
                    "spec": "./baseline-text-text.yaml",
                    "output_dir": "./out/shared",
                },
                {
                    "spec": "./network-degradation-fast-3g.yaml",
                    "output_dir": "./out/shared",
                },
            ]
        },
    )

    # When: the invalid batch file is loaded.
    # Then: validation rejects duplicate output directories.
    with pytest.raises(ValidationError, match="Each benchmark batch job must use its own output directory\\."):
        BenchmarkBatchSpec.from_file(batch_path)


def test_benchmark_batch_spec_resolves_paths_relative_to_batch_file(tmp_path: Path) -> None:
    # Given: one batch file with relative benchmark spec and output directory paths.
    batch_path = tmp_path / "resources/evaluation/all.yaml"
    first_spec_path = tmp_path / "resources/evaluation/baseline-text-text.yaml"
    second_spec_path = tmp_path / "resources/evaluation/network-degradation-fast-3g.yaml"
    write_yaml(
        first_spec_path,
        {
            "slug": "baseline-text-text",
            "description": "Baseline benchmark.",
            "benchmark": {
                "click_delay_ms": 300,
                "iat_slug": "sample-iat",
                "plan_seed": 123,
                "run_count": 5,
            },
        },
    )
    write_yaml(
        second_spec_path,
        {
            "slug": "network-degradation-fast-3g",
            "description": "Network benchmark.",
            "benchmark": {
                "click_delay_ms": 300,
                "iat_slug": "sample-iat",
                "plan_seed": 123,
                "run_count": 5,
                "network_emulation": {
                    "download_throughput_kbps": 1600,
                    "latency_ms": 150,
                    "upload_throughput_kbps": 750,
                },
            },
        },
    )
    write_yaml(
        batch_path,
        {
            "jobs": [
                {
                    "spec": "./baseline-text-text.yaml",
                    "output_dir": "../evaluation-results/baseline-text-text",
                },
                {
                    "spec": "./network-degradation-fast-3g.yaml",
                    "output_dir": "../evaluation-results/network-degradation-fast-3g",
                },
            ]
        },
    )

    # When: the batch file is resolved against its own directory.
    resolved_batch = BenchmarkBatchSpec.from_file(batch_path).resolve(batch_path.parent)

    # Then: each job path resolves to one absolute validated path.
    assert resolved_batch.jobs[0].spec == first_spec_path.resolve()
    assert resolved_batch.jobs[0].output_dir == (tmp_path / "resources/evaluation-results/baseline-text-text").resolve()
    assert resolved_batch.jobs[1].spec == second_spec_path.resolve()
    assert (
        resolved_batch.jobs[1].output_dir
        == (tmp_path / "resources/evaluation-results/network-degradation-fast-3g").resolve()
    )
