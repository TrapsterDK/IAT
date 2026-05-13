"""Typer application for repository maintenance commands."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Annotated, Literal

import click
import typer
from typer.main import get_group

from libs.bazel.workspace import get_build_working_directory, get_build_workspace_directory
from tools.cli.command.build import run_build
from tools.cli.command.configure import run_configure
from tools.cli.command.format import run_format
from tools.cli.command.lint import run_lint
from tools.cli.command.test import run_test
from tools.cli.command.update import run_update
from tools.cli.exceptions import (
    BUILD_WORKING_DIRECTORY_ERROR,
    BUILD_WORKSPACE_DIRECTORY_ERROR,
    CliToolError,
    CliUsageError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def _require_build_workspace_directory(environment: Mapping[str, str]) -> Path:
    workspace = get_build_workspace_directory(environment)
    if workspace is None:
        raise CliUsageError(BUILD_WORKSPACE_DIRECTORY_ERROR)

    return workspace


def _require_build_working_directory(environment: Mapping[str, str]) -> Path:
    directory = get_build_working_directory(environment)
    if directory is None:
        raise CliUsageError(BUILD_WORKING_DIRECTORY_ERROR)

    return directory


def _environment_and_workspace() -> tuple[Mapping[str, str], Path]:
    """Return the explicit CLI environment and workspace.

    Returns:
        The process environment and resolved workspace root.
    """
    environment = os.environ
    return environment, _require_build_workspace_directory(environment)


def _environment_workspace_and_directory() -> tuple[Mapping[str, str], Path, Path]:
    """Return the explicit CLI environment, workspace, and working directory.

    Returns:
        The process environment, resolved workspace, and resolved working directory.
    """
    environment, workspace = _environment_and_workspace()
    return environment, workspace, _require_build_working_directory(environment)


@app.command("format", help="Format repository files.")
def format_command(
    bazel_flags: Annotated[list[str] | None, typer.Option("--bazel_flag")] = None,
    fix: Annotated[bool, typer.Option("--fix/--no-fix")] = True,
    targets: Annotated[list[str] | None, typer.Argument()] = None,
) -> None:
    """Format repository files.

    Args:
        bazel_flags: Extra Bazel flags passed through to the formatter build.
        fix: Whether to apply formatting changes instead of running in check mode.
        targets: Optional formatter inputs to scope the run to.

    """
    environment, workspace, working_directory = _environment_workspace_and_directory()

    run_format(
        bazel_flags or [],
        fix,
        targets or [],
        workspace,
        working_directory,
        environment,
    )


@app.command("build", help="Build Bazel targets or files.")
def build_command(
    bazel_flags: Annotated[list[str] | None, typer.Option("--bazel_flag")] = None,
    targets: Annotated[list[str] | None, typer.Argument()] = None,
) -> None:
    """Build Bazel targets or files.

    Args:
        bazel_flags: Extra Bazel flags passed through to Bazel build.
        targets: Optional Bazel targets or file paths to build.

    """
    environment, workspace, working_directory = _environment_workspace_and_directory()
    run_build(bazel_flags or [], targets or [], workspace, working_directory, environment)


@app.command("test", help="Test Bazel targets or files.")
def bazel_test_command(
    bazel_flags: Annotated[list[str] | None, typer.Option("--bazel_flag")] = None,
    targets: Annotated[list[str] | None, typer.Argument()] = None,
) -> None:
    """Test Bazel targets or files.

    Args:
        bazel_flags: Extra Bazel flags passed through to Bazel test.
        targets: Optional Bazel targets or file paths to test.

    """
    environment, workspace, working_directory = _environment_workspace_and_directory()
    run_test(bazel_flags or [], targets or [], workspace, working_directory, environment)


@app.command("lint", help="Run lint and static analysis checks.")
def lint_command(
    bazel_flags: Annotated[list[str] | None, typer.Option("--bazel_flag")] = None,
    fix: Annotated[bool, typer.Option("--fix/--no-fix")] = True,
    output: Annotated[Literal["human", "machine"], typer.Option("--output")] = "human",
    targets: Annotated[list[str] | None, typer.Argument()] = None,
) -> None:
    """Run lint and static analysis checks.

    Args:
        bazel_flags: Extra Bazel flags passed through to the lint build.
        fix: Whether to apply lint fixes instead of running in check mode.
        output: Whether lint should emit human or machine output artifacts.
        targets: Optional Bazel targets or file paths to lint.

    """
    environment, workspace, working_directory = _environment_workspace_and_directory()
    run_lint(
        bazel_flags or [],
        fix,
        targets or [],
        workspace,
        working_directory,
        environment,
        output,
    )


@app.command("configure", help="Refresh Bazel BUILD files.")
def configure_command(
    bazel_flags: Annotated[list[str] | None, typer.Option("--bazel_flag")] = None,
) -> None:
    """Refresh Bazel BUILD files.

    Args:
        bazel_flags: Extra Bazel flags passed through to Gazelle.

    """
    environment, workspace = _environment_and_workspace()
    run_configure(bazel_flags or [], workspace, environment)


@app.command("update", help="Refresh lockfiles and dependency metadata.")
def update_command(
    bazel_flags: Annotated[list[str] | None, typer.Option("--bazel_flag")] = None,
    targets: Annotated[list[str] | None, typer.Argument()] = None,
) -> None:
    """Refresh lockfiles and dependency metadata.

    Args:
        bazel_flags: Extra Bazel flags passed through to Bazel update commands.
        targets: Optional update groups to run.

    """
    environment, workspace = _environment_and_workspace()
    run_update(bazel_flags or [], targets or [], workspace, environment)


tool_command = get_group(app)


def get_registered_command(command_name: str) -> click.Command:
    """Return one registered subcommand directly.

    Args:
        command_name: The subcommand name to resolve.

    Returns:
        The resolved Click subcommand.
    """
    command = tool_command.commands.get(command_name)
    if command is None:
        raise RuntimeError(f"Unknown CLI command: {command_name}")
    return command


def _run_click_command(command: click.Command, args: list[str], program_name: str) -> int:
    """Run one Click command with explicit exit-code handling.

    Args:
        command: The Click command to invoke.
        args: Command-line arguments to pass through.
        program_name: The program name shown in Click messages.

    Returns:
        The resulting process exit code.
    """
    try:
        command.main(args=args, prog_name=program_name, standalone_mode=False)
    except CliToolError as error:
        return error.exit_code
    except SystemExit as error:
        if error.code is None:
            return 0
        if isinstance(error.code, int):
            return error.code
        return 1
    except click.ClickException as error:
        error.show()
        return error.exit_code

    return 0


def run_tool_command(args: Sequence[str]) -> int:
    """Run the root `tool` command with explicit args.

    Args:
        args: Command-line arguments to pass to the root tool command.

    Returns:
        The process exit code returned by the CLI.
    """
    return _run_click_command(tool_command, list(args), "tool")


def run_specific_command(command_name: str, args: Sequence[str]) -> int:
    """Run one subcommand with explicit args.

    Args:
        command_name: The subcommand name to run.
        args: Command-line arguments to pass to that subcommand.

    Returns:
        The process exit code returned by the subcommand.
    """
    return _run_click_command(get_registered_command(command_name), list(args), command_name)
