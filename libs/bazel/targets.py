"""Helpers for resolving mixed inputs into Bazel targets."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from libs.bazel.command import run_bazel_command
from libs.bazel.workspace import WorkspacePathError, resolve_workspace_path

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from pathlib import Path


class TargetResolutionError(RuntimeError):
    """Raised when file-path inputs cannot be resolved to Bazel targets."""


def _path_to_file_label(path: Path, workspace: Path, working_directory: Path) -> str:
    try:
        relative_path = resolve_workspace_path(path, workspace, working_directory)
    except WorkspacePathError as error:
        raise TargetResolutionError(f"Finding targets for specified paths failed: {error}") from error

    package = relative_path.parent.as_posix()
    if package in {"", "."}:
        return f"//:{relative_path.name}"

    return f"//{package}:{relative_path.name}"


def split_targets_and_paths(inputs: Collection[str]) -> tuple[list[str], list[str]]:
    """Split targets and file paths from a mixed list of inputs.

    Args:
        inputs: The mixed list of Bazel targets and file paths.

    Returns:
        A tuple of Bazel targets and file paths.
    """
    targets: list[str] = []
    paths: list[str] = []

    for item in inputs:
        if item.startswith(("//", ":", "@")):
            targets.append(item)
        else:
            paths.append(item)

    return targets, paths


def bazel_paths_to_targets(
    paths: list[Path],
    workspace: Path,
    working_directory: Path,
    environment: Mapping[str, str],
) -> list[str]:
    """Resolve workspace file paths to Bazel rule targets.

    Args:
        paths: Workspace file paths to resolve.
        workspace: The workspace root for Bazel invocation.
        working_directory: The working directory used to resolve relative paths.
        environment: Explicit process environment used to run Bazel query.

    Returns:
        Matching Bazel rule targets.

    Raises:
        RuntimeError: At least one path cannot be resolved to a Bazel rule target.
    """
    if not paths:
        return []

    query = "kind(rule, same_pkg_direct_rdeps(set({})))".format(
        " ".join(_path_to_file_label(path, workspace, working_directory) for path in paths)
    )
    result = run_bazel_command(
        ["query", "-k", query],
        workspace,
        environment,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    if result.returncode not in (0, 3):
        raise TargetResolutionError(
            f"Finding targets for specified paths failed with Bazel query exit code {result.returncode}."
        )

    matched_targets = [line for line in result.stdout.splitlines() if line]
    if not matched_targets:
        raise TargetResolutionError("Finding targets for specified paths failed.")

    return matched_targets
