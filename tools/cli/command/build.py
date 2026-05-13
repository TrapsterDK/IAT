"""Implementation of the `build` command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from libs.bazel.command import run_bazel_command
from tools.cli.exceptions import CliToolError
from tools.cli.target_resolution import resolve_command_inputs_to_targets

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def run_build(
    bazel_flags: list[str],
    targets: list[str],
    workspace: Path,
    build_working_directory: Path,
    environment: Mapping[str, str],
) -> None:
    """Run Bazel build with optional file-path target resolution.

    Args:
        bazel_flags: Extra Bazel flags to pass through.
        targets: CLI-supplied labels or file paths to build.
        workspace: The Bazel workspace root.
        build_working_directory: The Bazel invocation directory.
        environment: Explicit process environment for Bazel.

    Raises:
        CliToolError: Bazel exits with a non-zero status.
    """
    selected_targets = resolve_command_inputs_to_targets(
        targets,
        workspace,
        build_working_directory,
        environment,
    )

    result = run_bazel_command(["build", *bazel_flags, *selected_targets], workspace, environment)
    if result.returncode != 0:
        raise CliToolError(result.returncode)
