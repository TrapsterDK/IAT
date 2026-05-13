"""Implementation of the `update` command."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

from libs.bazel.command import run_bazel_command
from tools.cli.exceptions import CliToolError, CliUsageError

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from pathlib import Path


_VALID_TARGETS = {"bazel", "python", "javascript"}


def _run_bazel_step(
    workspace: Path,
    environment: Mapping[str, str],
    completion_message: str,
    arguments: Sequence[str],
) -> None:
    started_at = time.monotonic()
    result = run_bazel_command(arguments, workspace, environment)
    if result.returncode != 0:
        raise CliToolError(result.returncode)

    sys.stdout.write(f"{completion_message} ({time.monotonic() - started_at:.2f}s)\n")


def _validate_targets(targets: Collection[str], valid_targets: set[str]) -> set[str]:
    selected_targets = set(targets)
    invalid_targets = selected_targets - valid_targets
    if invalid_targets:
        invalid = ", ".join(invalid_targets)
        raise RuntimeError(f"Invalid target specified for update: {invalid}")
    return selected_targets


def _selected_targets(targets: Collection[str]) -> set[str]:
    selected_targets = _validate_targets(targets, _VALID_TARGETS)
    return selected_targets or _VALID_TARGETS


def run_update(
    bazel_flags: list[str],
    targets: Collection[str],
    workspace: Path,
    environment: Mapping[str, str],
) -> None:
    """Refresh dependency and lock metadata.

    Args:
        bazel_flags: Extra Bazel flags passed through to Bazel update commands.
        targets: Optional update groups to run.
        workspace: The Bazel workspace root.
        environment: Environment variables used to run Bazel update commands.

    Raises:
        CliUsageError: The selected target groups are invalid.
        CliToolError: An update step exits with a non-zero status.
    """
    try:
        selected_targets = _selected_targets(targets)
    except RuntimeError as error:
        raise CliUsageError(str(error)) from error

    # JavaScript updates can change module extension facts through package.json,
    # so refresh MODULE.bazel.lock before generating the JS lockfile as well.
    if "bazel" in selected_targets or "javascript" in selected_targets:
        _run_bazel_step(
            workspace,
            environment,
            "Updated Bazel dependencies.",
            ("mod", "deps", *bazel_flags, "--lockfile_mode=update"),
        )
        _run_bazel_step(
            workspace,
            environment,
            "Tidied Bazel modules.",
            ("mod", "tidy", *bazel_flags),
        )

    if "python" in selected_targets:
        _run_bazel_step(
            workspace,
            environment,
            "Generated Python lockfile.",
            ("run", *bazel_flags, "//tools/python:lock"),
        )
        _run_bazel_step(
            workspace,
            environment,
            "Updated Gazelle Python manifest.",
            ("run", *bazel_flags, "//tools/python:gazelle_manifest.update"),
        )

    if "javascript" in selected_targets:
        _run_bazel_step(
            workspace,
            environment,
            "Generated JavaScript lockfile.",
            ("run", *bazel_flags, "//tools/javascript:lock"),
        )
