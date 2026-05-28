"""Grid-backed WebDriver benchmark runner implementation."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.options import ArgOptions

from apps.evaluation.result_models import (
    BenchmarkJobResult,
    WorkerBenchmarkResult,
    WorkerInfo,
)
from apps.evaluation.runfiles import load_browser_harness

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from yarl import URL

    from apps.evaluation.grid import GridWorker
    from apps.evaluation.specs import BenchmarkSettings, NetworkEmulationSettings


BENCHMARK_TIMEOUT_SECONDS = 600
HARNESS_EXECUTION_SOURCE = """
const callback = arguments[arguments.length - 1];
window.__iatEvaluation
  .runBenchmark(arguments[0])
  .then((result) => callback({ ok: true, result }))
  .catch((error) => callback({ ok: false, error: String(error) }));
"""


class BrowserHarnessResponse(BaseModel):
    """Validated browser harness response payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    result: WorkerBenchmarkResult | None = None
    error: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> BrowserHarnessResponse:
        """Require exactly one matching success or failure payload.

        Returns:
            The validated harness response.
        """
        if self.ok:
            if self.result is None or self.error is not None:
                raise ValueError("Successful harness responses must include one result and no error.")
        elif self.result is not None or self.error is None:
            raise ValueError("Failed harness responses must include one error and no result.")

        return self


def run_benchmark_job(
    command_executor_url: URL,
    worker: GridWorker,
    benchmark_settings: BenchmarkSettings,
    app_url: URL,
) -> BenchmarkJobResult:
    """Run one benchmark spec against one discovered Grid worker.

    Args:
        command_executor_url: Selenium Grid router URL.
        worker: Discovered evaluation worker.
        benchmark_settings: Benchmark settings executed against that worker.
        app_url: Base app URL used to derive the evaluation frontend URL.

    Returns:
        One typed benchmark job result with worker metadata and validated browser output.
    """
    driver: WebDriver | None = None
    try:
        driver = _build_cdp_driver(command_executor_url, worker)
        _apply_benchmark_environment(driver, benchmark_settings)

        return BenchmarkJobResult(
            worker=_build_worker_info(worker, driver.capabilities),
            result=_run_browser_harness(driver, benchmark_settings, app_url),
        )
    finally:
        if driver is not None:
            with contextlib.suppress(Exception):
                driver.quit()


def _run_browser_harness(
    driver: WebDriver,
    benchmark_settings: BenchmarkSettings,
    app_url: URL,
) -> WorkerBenchmarkResult:
    driver.set_script_timeout(BENCHMARK_TIMEOUT_SECONDS * benchmark_settings.run_count)
    driver.get(_build_evaluation_url(app_url, benchmark_settings.plan_seed))
    driver.execute_script(load_browser_harness())
    try:
        harness_response = BrowserHarnessResponse.model_validate(
            driver.execute_async_script(
                HARNESS_EXECUTION_SOURCE,
                {
                    "clickDelayMs": benchmark_settings.click_delay_ms,
                    "iatSlug": benchmark_settings.iat_slug,
                    "sessionCount": benchmark_settings.run_count,
                },
            )
        )
    except ValidationError as error:
        raise RuntimeError(f"Benchmark harness returned one invalid response payload: {error}") from error

    if harness_response.ok and harness_response.result is not None:
        return harness_response.result

    raise RuntimeError(f"Benchmark run failed: {harness_response.error or 'unknown error'}")


def _build_worker_info(worker: GridWorker, session_capabilities: dict[str, object]) -> WorkerInfo:
    return WorkerInfo(
        worker_id=worker.worker_id,
        browser_name=_optional_capability_text(session_capabilities, "browserName") or worker.browser_name,
        browser_version=_optional_capability_text(session_capabilities, "browserVersion"),
        platform_name=_optional_capability_text(session_capabilities, "platformName"),
    )


def _optional_capability_text(session_capabilities: dict[str, object], field_name: str) -> str | None:
    value = session_capabilities.get(field_name)
    return value if isinstance(value, str) and value else None


def _apply_benchmark_environment(driver: WebDriver, benchmark_settings: BenchmarkSettings) -> None:
    requires_cdp = benchmark_settings.cpu_emulation is not None or benchmark_settings.network_emulation is not None
    if not requires_cdp:
        return

    if not _supports_cdp(driver):
        raise RuntimeError(
            "Benchmark environment setup requires one session with CDP support. "
            f"Received browserName={driver.capabilities.get('browserName')} without CDP support."
        )

    if benchmark_settings.cpu_emulation is not None:
        _apply_cpu_throttling(driver, benchmark_settings.cpu_emulation.rate)

    if benchmark_settings.network_emulation is not None:
        _apply_network_emulation(driver, benchmark_settings.network_emulation)


def _supports_cdp(driver: WebDriver) -> bool:
    try:
        driver.execute_cdp_cmd("Browser.getVersion", {})
    except WebDriverException:
        return False

    return True


def _apply_cpu_throttling(driver: WebDriver, cpu_throttling_rate: float) -> None:
    try:
        driver.execute_cdp_cmd("Emulation.setCPUThrottlingRate", {"rate": cpu_throttling_rate})
    except WebDriverException as error:
        raise RuntimeError(f"Failed to apply CPU throttling via CDP: {error}") from error


def _apply_network_emulation(driver: WebDriver, network_emulation: NetworkEmulationSettings) -> None:
    download_throughput = _kbps_to_bytes_per_second(network_emulation.download_throughput_kbps)
    upload_throughput = _kbps_to_bytes_per_second(network_emulation.upload_throughput_kbps)
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
        driver.execute_cdp_cmd(
            "Network.emulateNetworkConditions",
            {
                "downloadThroughput": download_throughput,
                "latency": network_emulation.latency_ms,
                "offline": False,
                "uploadThroughput": upload_throughput,
            },
        )
    except WebDriverException as error:
        raise RuntimeError(f"Failed to apply network emulation via CDP: {error}") from error


def _kbps_to_bytes_per_second(throughput_kbps: int) -> int:
    return int(throughput_kbps * 1000 / 8)


def _build_cdp_driver(command_executor_url: URL, worker: GridWorker) -> WebDriver:
    options = ArgOptions()
    options.set_capability("browserName", worker.browser_name)
    options.set_capability("iat:workerId", worker.worker_id)

    return webdriver.Remote(command_executor=str(command_executor_url), options=options)


def _build_evaluation_url(app_url: URL, plan_seed: int) -> str:
    return str(app_url.update_query(plan_seed=str(plan_seed), session_mode="evaluation"))
