"""Implementation of the `format` command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from libs.bazel.artifacts import BuiltBinaryError, build_binary, run_built_binary
from libs.bazel.targets import split_targets_and_paths
from libs.bazel.workspace import WorkspacePathError, resolve_workspace_path
from tools.cli.exceptions import CliToolError, CliUsageError

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping


def _validated_paths(paths: list[str], workspace: Path, cwd: Path) -> list[str]:
    validated_paths: list[str] = []

    for path in paths:
        path_object = Path(path)
        try:
            validated_paths.append(resolve_workspace_path(path_object, workspace, cwd).as_posix())
        except WorkspacePathError as error:
            raise CliUsageError(str(error)) from error

    return validated_paths


def run_format(
    bazel_flags: list[str],
    fix: bool,
    targets: Collection[str],
    workspace: Path,
    cwd: Path,
    environment: Mapping[str, str],
) -> None:
    """Run the repository formatting workflow."""
    labels, paths = split_targets_and_paths(targets)
    if labels:
        raise CliUsageError("Specifying targets is not supported for format command.")

    formatter_paths = _validated_paths(paths, workspace, cwd)
    build_target = "//tools/format:format" if fix else "//tools/format:format.check"

    try:
        formatter = build_binary(build_target, bazel_flags, workspace=workspace, environment=environment)
    except BuiltBinaryError as error:
        raise CliToolError(error.exit_code, str(error)) from error

    result = run_built_binary(formatter, formatter_paths, workspace, cwd, environment)
    if result.returncode != 0:
        raise CliToolError(result.returncode)
