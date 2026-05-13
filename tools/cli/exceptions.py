"""CLI exception types."""

from __future__ import annotations

from typing import IO, Any

import click

BUILD_WORKSPACE_DIRECTORY_ERROR = (
    "BUILD_WORKSPACE_DIRECTORY is required. Run this command through `bazel run`, or provide "
    "BUILD_WORKSPACE_DIRECTORY explicitly in tests or wrappers. It is not guaranteed when running "
    "the CLI directly as a standalone binary or Python module."
)

BUILD_WORKING_DIRECTORY_ERROR = (
    "BUILD_WORKING_DIRECTORY is required. Run the CLI through `bazel run`, or provide "
    "BUILD_WORKING_DIRECTORY explicitly when invoking it in tests or wrappers. "
    "This variable is not guaranteed when running the binary or Python module directly."
)


class CliExitError(click.ClickException):
    """Raised for CLI failures that should terminate the process."""

    def __init__(self, exit_code: int, message: str | None = None) -> None:
        """Initialize the CLI exit error.

        Args:
            exit_code: The process exit code to use for this failure.
            message: Optional user-facing error message.
        """
        super().__init__(message or "")
        self.exit_code = exit_code

    def show(self, file: IO[Any] | None = None) -> None:
        """Emit the user-facing error message if one is available.

        Args:
            file: Optional output stream for the rendered message.
        """
        if not self.message:
            return
        if file is None:
            file = click.get_text_stream("stderr")
        click.echo(f"{click.style('ERROR:', fg='red')} {self.message}", file=file)


class CliUsageError(CliExitError):
    """Raised for user-facing CLI usage and setup failures."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        """Initialize the CLI usage error.

        Args:
            message: The user-facing error message.
            exit_code: The process exit code to use for this failure.
        """
        super().__init__(exit_code, message)


class CliToolError(CliExitError):
    """Raised for underlying tool failures with a real process exit code."""

    def __init__(self, exit_code: int, message: str | None = None) -> None:
        """Initialize the CLI tool error.

        Args:
            exit_code: The underlying tool exit code.
            message: Optional user-facing error message.
        """
        super().__init__(exit_code, message)
