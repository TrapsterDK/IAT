"""Implementation of the `lint` command."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from libs.bazel.bep import iter_named_set_files, load_events
from libs.bazel.command import run_bazel_command
from tools.cli.exceptions import CliToolError, CliUsageError
from tools.cli.target_resolution import resolve_command_inputs_to_targets

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _apply_patch(path: Path, patch_executable: str, workspace: Path, dry_run: bool = False) -> None:
    command = [patch_executable]
    if dry_run:
        command.append("--dry-run")
    command.extend(["-p1", f"--input={path}"])

    result = subprocess.run(command, check=False, cwd=workspace)  # noqa: S603
    if result.returncode != 0:
        raise CliUsageError(f"Failed to apply patch {path}")


def _apply_patches(patches: list[Path], workspace: Path) -> None:
    if not patches:
        return

    patch_executable = shutil.which("patch")
    if patch_executable is None:
        raise CliUsageError("Lint fix mode requires the `patch` executable.")

    ordered_patches = sorted(patches)
    for patch in ordered_patches:
        _apply_patch(patch, patch_executable, workspace, dry_run=True)

    for patch in ordered_patches:
        _apply_patch(patch, patch_executable, workspace)


def _run_gazelle_check(bazel_flags: list[str], workspace: Path, environment: Mapping[str, str]) -> None:
    result = run_bazel_command(["run", *bazel_flags, "//tools:gazelle.check"], workspace, environment)
    if result.returncode != 0:
        raise CliToolError(result.returncode)


def _collect_artifacts(bep_path: Path) -> tuple[int, list[Path]]:
    exit_code = 0
    patches: list[Path] = []

    if not bep_path.exists():
        return exit_code, patches

    for artifact in iter_named_set_files(load_events(bep_path)):
        if not artifact.path.exists():
            continue

        if artifact.logical_name.endswith(".out"):
            sys.stderr.write(_read_text(artifact.path))
        elif artifact.logical_name.endswith(".report"):
            report = _read_text(artifact.path)
            if '"results": [' in report:
                sys.stdout.write(report)
        elif artifact.logical_name.endswith(".patch"):
            patches.append(artifact.path)
        elif artifact.logical_name.endswith(".exit_code") and int(_read_text(artifact.path).rstrip()) != 0:
            exit_code = 1

    return exit_code, patches


def run_lint(
    bazel_flags: list[str],
    fix: bool,
    targets: Collection[str],
    workspace: Path,
    build_working_directory: Path,
    environment: Mapping[str, str],
    output_mode: str,
) -> None:
    """Run the repository lint workflow.

    Args:
        bazel_flags: Extra Bazel flags to pass through.
        fix: Whether lint should apply available fixes.
        targets: CLI-supplied labels or file paths to lint.
        workspace: The Bazel workspace root.
        build_working_directory: The Bazel invocation directory.
        environment: Explicit process environment for Bazel.
        output_mode: Requested lint output group mode.

    Raises:
        CliToolError: Gazelle or lint exits with a non-zero status.
        CliUsageError: Fix mode cannot apply generated patches.
    """
    selected_targets = resolve_command_inputs_to_targets(
        targets,
        workspace,
        build_working_directory,
        environment,
    )

    gazelle_exit_code = 0
    try:
        _run_gazelle_check(bazel_flags, workspace, environment)
    except CliToolError as error:
        gazelle_exit_code = error.exit_code

    with tempfile.TemporaryDirectory(prefix=f"{workspace.name}-tool-lint-") as temp_dir:
        bep_path = Path(temp_dir) / "build_event.json"
        fix_flags = ["--output_groups=rules_lint_patch", "--@aspect_rules_lint//lint:fix"] if fix else []
        build = run_bazel_command(
            [
                "build",
                *bazel_flags,
                "--config=lint",
                "--remote_download_regex=.*AspectRulesLint.*",
                *fix_flags,
                f"--output_groups=rules_lint_{output_mode}",
                f"--build_event_json_file={bep_path}",
                *selected_targets,
            ],
            workspace,
            environment,
        )
        exit_code, patches = _collect_artifacts(bep_path)

        if build.returncode != 0:
            raise CliToolError(build.returncode)

        if fix:
            _apply_patches(patches, workspace)

    if exit_code != 0:
        raise CliToolError(exit_code)

    if gazelle_exit_code != 0:
        raise CliToolError(gazelle_exit_code)
