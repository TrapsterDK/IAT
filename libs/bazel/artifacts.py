"""Helpers for building and executing Bazel artifacts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal, overload

from libs.bazel.command import process_environment, run_bazel_command

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from subprocess import CompletedProcess


class BuiltBinaryError(RuntimeError):
    """Raised when building one Bazel executable artifact fails."""

    def __init__(self, exit_code: int, message: str) -> None:
        """Initialize one built-binary failure.

        Args:
            exit_code: The underlying process exit code.
            message: The user-facing failure message.
        """
        super().__init__(message)
        self.exit_code = exit_code


def _built_binary_path(
    label: str,
    bazel_flags: Sequence[str],
    workspace: Path,
    environment: Mapping[str, str],
) -> Path:
    result = run_bazel_command(
        [
            "cquery",
            *bazel_flags,
            "--ui_event_filters=+stdout",
            label,
            "--output=starlark",
            "--starlark:expr=target.files_to_run.executable.path",
        ],
        workspace,
        environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        raise BuiltBinaryError(
            result.returncode,
            f"Resolving the built executable for Bazel target '{label}' failed with exit code {result.returncode}.",
        )

    executable = result.stdout.strip()
    if not executable:
        raise BuiltBinaryError(1, f"Bazel target '{label}' did not produce an executable artifact.")

    path = Path(executable)
    return path if path.is_absolute() else workspace / path


def build_binary(
    label: str,
    bazel_flags: Sequence[str],
    workspace: Path,
    environment: Mapping[str, str],
) -> Path:
    """Build a Bazel target and return the resulting executable.

    Args:
        label: The Bazel label to build.
        bazel_flags: Extra flags to pass to `bazel build`.
        workspace: The workspace root to run Bazel from.
        environment: Environment used for the Bazel subprocess.

    Returns:
        The built executable artifact.

    Raises:
        BuiltBinaryError: The build fails, the executable query fails, or the target is not executable.
    """
    result = run_bazel_command(["build", *bazel_flags, label], workspace, environment)
    if result.returncode != 0:
        raise BuiltBinaryError(
            result.returncode, f"Building Bazel target '{label}' failed with exit code {result.returncode}."
        )

    return _built_binary_path(label, bazel_flags, workspace, environment)


def _runfiles_manifest(runfiles_dir: Path) -> Path | None:
    for candidate in (Path(f"{runfiles_dir}_manifest"), runfiles_dir / "MANIFEST"):
        if candidate.is_file():
            return candidate
    return None


def _runfiles_env(env: Mapping[str, str], executable: Path, workspace: Path, working_directory: Path) -> dict[str, str]:
    runfiles_dir = Path(f"{executable}.runfiles")
    manifest = _runfiles_manifest(runfiles_dir)

    result = process_environment(env)
    test_tmpdir = env.get("TEST_TMPDIR")
    if test_tmpdir:
        result["TEST_TMPDIR"] = test_tmpdir

    if runfiles_dir.is_dir():
        result.update(
            {
                "RUNFILES_DIR": str(runfiles_dir),
                "RUNFILES": str(runfiles_dir),
                "JAVA_RUNFILES": str(runfiles_dir),
                "PYTHON_RUNFILES": str(runfiles_dir),
            }
        )
    if manifest is not None:
        result["RUNFILES_MANIFEST_FILE"] = str(manifest)

    result.update(
        {
            "BUILD_WORKSPACE_DIRECTORY": str(workspace),
            "BUILD_WORKING_DIRECTORY": str(working_directory),
        }
    )
    return result


@overload
def run_built_binary(
    executable: Path,
    args: Sequence[str],
    workspace: Path,
    working_directory: Path,
    environment: Mapping[str, str],
    stdout: int | None = None,
    stderr: int | None = None,
    text: Literal[False] = False,
) -> CompletedProcess[bytes]: ...


@overload
def run_built_binary(
    executable: Path,
    args: Sequence[str],
    workspace: Path,
    working_directory: Path,
    environment: Mapping[str, str],
    stdout: int | None = None,
    stderr: int | None = None,
    text: Literal[True] = True,
) -> CompletedProcess[str]: ...


def run_built_binary(
    executable: Path,
    args: Sequence[str],
    workspace: Path,
    working_directory: Path,
    environment: Mapping[str, str],
    stdout: int | None = None,
    stderr: int | None = None,
    text: bool = False,
) -> CompletedProcess[bytes] | CompletedProcess[str]:
    """Run a previously-built Bazel executable with runfiles configured.

    Args:
        executable: The built executable or its path.
        args: Command-line arguments to pass to the executable.
        workspace: The workspace root for runfiles-related environment variables.
        working_directory: The working directory for the subprocess.
        environment: The environment used as the base runfiles environment.
        stdout: Optional stdout redirection.
        stderr: Optional stderr redirection.
        text: Whether subprocess output should be decoded as text.

    Returns:
        The completed subprocess result.
    """
    return subprocess.run(  # noqa: S603
        [str(executable), *args],
        check=False,
        cwd=working_directory,
        env=_runfiles_env(environment, executable, workspace, working_directory),
        stdout=stdout,
        stderr=stderr,
        text=text,
    )
