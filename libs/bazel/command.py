"""Bazel process execution helpers."""

from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Literal, overload

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from subprocess import CompletedProcess

_NESTED_BAZEL_ENV_KEYS = (
    "BUILD_WORKSPACE_DIRECTORY",
    "BUILD_WORKING_DIRECTORY",
    "TEST_TMPDIR",
    "TEST_SRCDIR",
    "TEST_WORKSPACE",
    "RUNFILES_DIR",
    "RUNFILES",
    "PYTHON_RUNFILES",
    "JAVA_RUNFILES",
    "RUNFILES_MANIFEST_FILE",
)


def process_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Return a subprocess environment for nested Bazel calls.

    Args:
        environment: Explicit environment variables supplied by the caller.

    Returns:
        The explicit environment with Bazel-test-only state removed.
    """
    return {key: value for key, value in environment.items() if key not in _NESTED_BAZEL_ENV_KEYS}


def _bazel_command(arguments: Sequence[str], workspace: Path, environment: Mapping[str, str]) -> list[str]:
    """Return a Bazel command line for subprocess invocation.

    Args:
        arguments: Bazel subcommand arguments excluding the Bazel executable.
        workspace: Workspace root used to determine whether repo rc files exist.
        environment: Explicit environment variables supplied by the caller.

    Returns:
        A full Bazel command.
    """
    test_tmpdir = environment.get("TEST_TMPDIR")
    startup_flags: list[str] = []

    workspace_bazelrc = workspace / ".bazelrc"
    if not workspace_bazelrc.is_file():
        startup_flags.append("--ignore_all_rc_files")
    else:
        startup_flags.extend(
            [
                "--nosystem_rc",
                "--nohome_rc",
                "--noworkspace_rc",
                f"--bazelrc={workspace_bazelrc.resolve()}",
            ]
        )

    if not test_tmpdir:
        return ["bazel", *startup_flags, *arguments]

    install_base = Path(test_tmpdir) / "bazel-install-base"
    install_base.parent.mkdir(parents=True, exist_ok=True)
    startup_flags.append(f"--install_base={install_base}")

    output_base_root = Path(test_tmpdir) / "bazel-output-bases"
    output_base_root.mkdir(parents=True, exist_ok=True)
    workspace_key = sha256(str(workspace.resolve()).encode("utf-8")).hexdigest()[:12]
    output_base = output_base_root / workspace_key
    startup_flags.append(f"--output_base={output_base}")

    return ["bazel", *startup_flags, *arguments]


@overload
def run_bazel_command(
    arguments: Sequence[str],
    workspace: Path,
    environment: Mapping[str, str],
    stdout: int | None = None,
    stderr: int | None = None,
    text: Literal[False] = False,
) -> CompletedProcess[bytes]: ...


@overload
def run_bazel_command(
    arguments: Sequence[str],
    workspace: Path,
    environment: Mapping[str, str],
    stdout: int | None = None,
    stderr: int | None = None,
    text: Literal[True] = True,
) -> CompletedProcess[str]: ...


def run_bazel_command(
    arguments: Sequence[str],
    workspace: Path,
    environment: Mapping[str, str],
    stdout: int | None = None,
    stderr: int | None = None,
    text: bool = False,
) -> CompletedProcess[bytes] | CompletedProcess[str]:
    """Run Bazel with repository-specific command and environment handling.

    Args:
        arguments: Bazel subcommand arguments excluding the Bazel executable.
        workspace: Workspace root used for command construction and default cwd.
        environment: Explicit environment variables supplied by the caller.
        stdout: Optional stdout redirection.
        stderr: Optional stderr redirection.
        text: Whether subprocess output should be decoded as text.

    Returns:
        The completed Bazel subprocess result.
    """
    return subprocess.run(  # noqa: S603
        _bazel_command(arguments, workspace=workspace, environment=environment),
        check=False,
        cwd=workspace,
        env=process_environment(environment),
        stdout=stdout,
        stderr=stderr,
        text=text,
    )
