"""Executable entrypoint for the repository CLI."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from tools.cli.app import run_tool_command

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(args: Sequence[str]) -> int:
    """Run the repository CLI entrypoint.

    Args:
        args: The command-line arguments to run the CLI with.

    Returns:
        The process exit code returned by the CLI.
    """
    return run_tool_command(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
