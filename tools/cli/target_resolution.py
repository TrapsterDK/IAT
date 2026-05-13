"""Helpers for resolving CLI command inputs to Bazel targets."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from libs.bazel.command import run_bazel_command
from libs.bazel.targets import TargetResolutionError, bazel_paths_to_targets, split_targets_and_paths
from tools.cli.exceptions import CliUsageError

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

PATH_RESOLUTION_ERROR = "Finding targets for specified paths failed."


def _ordered_unique(items: Iterable[str]) -> list[str]:
    """Return one ordered list with duplicate targets removed."""
    ordered_items: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered_items.append(item)
    return ordered_items


def _filter_path_resolved_targets_for_cli(
    targets: list[str],
    workspace: Path,
    environment: Mapping[str, str],
) -> list[str]:
    """Apply CLI-specific policy filters to path-resolved targets."""
    if not targets:
        return []

    target_set = "set({})".format(" ".join(targets))
    result = run_bazel_command(
        ["query", "-k", f"{target_set} except attr(tags, manual, {target_set})"],
        workspace,
        environment,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    if result.returncode not in (0, 3):
        raise RuntimeError(f"Filtering resolved targets failed with Bazel query exit code {result.returncode}.")

    allowed_targets = {line for line in result.stdout.splitlines() if line and not line.endswith(".venv")}
    return [target for target in targets if target in allowed_targets]


def resolve_command_inputs_to_targets(
    inputs: Collection[str],
    workspace: Path,
    build_working_directory: Path,
    environment: Mapping[str, str],
) -> list[str]:
    """Resolve CLI inputs when file paths require an invocation directory.

    Args:
        inputs: Command inputs that may contain labels and file paths.
        workspace: The Bazel workspace root.
        build_working_directory: The Bazel invocation directory.
        environment: Explicit process environment used to run Bazel query.

    Returns:
        The selected Bazel targets.

    Raises:
        CliUsageError: The inputs are invalid.
    """
    if not inputs:
        return ["//..."]

    labels, paths = split_targets_and_paths(inputs)
    if not paths:
        return _ordered_unique(labels)

    try:
        resolved_path_targets = bazel_paths_to_targets(
            [Path(path) for path in paths], workspace, build_working_directory, environment
        )
    except TargetResolutionError as error:
        raise CliUsageError(PATH_RESOLUTION_ERROR) from error

    filtered_targets = _filter_path_resolved_targets_for_cli(resolved_path_targets, workspace, environment)
    selected_targets = [*labels, *filtered_targets]
    if not selected_targets:
        raise CliUsageError(PATH_RESOLUTION_ERROR)

    return _ordered_unique(selected_targets)
