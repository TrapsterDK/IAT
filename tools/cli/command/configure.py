"""Implementation of the `configure` command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from libs.bazel.command import run_bazel_command
from libs.bazel.workspace import iter_build_files
from tools.cli.exceptions import CliToolError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

BUILD_BAZEL_MARKER = b'name = "build_bazel"'
BUILD_BAZEL_FILEGROUP = b"""filegroup(
    name = "build_bazel",
    srcs = ["BUILD.bazel"],
    tags = ["starlark"],
)"""


def _ensure_build_bazel_filegroups(workspace: Path) -> None:
    for build_file in iter_build_files(workspace):
        with build_file.open("rb+") as file:
            contents = file.read()
            if BUILD_BAZEL_MARKER in contents:
                continue

            if contents.endswith(b"\n\n"):
                pass
            elif contents.endswith(b"\n"):
                file.write(b"\n")
            else:
                file.write(b"\n\n")

            file.write(BUILD_BAZEL_FILEGROUP)


def run_configure(bazel_flags: list[str], workspace: Path, environment: Mapping[str, str]) -> None:
    """Refresh Bazel BUILD files using Gazelle.

    Args:
        bazel_flags: Extra Bazel flags passed through to Gazelle.
        workspace: The Bazel workspace root.
        environment: Explicit process environment used to run Bazel.

    Raises:
        CliToolError: Gazelle exits with a non-zero status.
    """
    result = run_bazel_command(["run", *bazel_flags, "//tools:gazelle"], workspace, environment)
    if result.returncode != 0:
        raise CliToolError(result.returncode)

    _ensure_build_bazel_filegroups(workspace)
