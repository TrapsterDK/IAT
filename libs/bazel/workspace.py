"""Workspace scanning helpers and Bazel invocation context accessors."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


class WorkspacePathError(RuntimeError):
    """Raised when one filesystem path cannot be resolved inside a workspace."""


def get_build_working_directory(environment: Mapping[str, str]) -> Path | None:
    """Return the Bazel-reported `BUILD_WORKING_DIRECTORY`.

    Args:
        environment: Explicit process environment used to resolve Bazel working-directory variables.

    Returns:
        The working directory reported by Bazel, or `None` if unavailable.
    """
    path = environment.get("BUILD_WORKING_DIRECTORY")
    if path:
        return Path(path).resolve()

    return None


def get_build_workspace_directory(environment: Mapping[str, str]) -> Path | None:
    """Return the Bazel-reported `BUILD_WORKSPACE_DIRECTORY`.

    Args:
        environment: Explicit process environment used to resolve Bazel workspace variables.

    Returns:
        The workspace root reported by Bazel, or `None` if unavailable.
    """
    path = environment.get("BUILD_WORKSPACE_DIRECTORY")
    if path:
        return Path(path).resolve()

    return None


def resolve_workspace_path(path: Path, workspace: Path, working_directory: Path) -> Path:
    """Resolve one path against a workspace-aware working directory.

    Args:
        path: The user-supplied path to resolve.
        workspace: The Bazel workspace root.
        working_directory: The Bazel invocation directory for relative paths.

    Returns:
        The resolved path relative to the workspace root.

    Raises:
        WorkspacePathError: The path does not exist or resolves outside the workspace.
    """
    workspace = workspace.resolve()
    working_directory = working_directory.resolve()

    unresolved_path = path if path.is_absolute() else working_directory / path
    resolved_path = unresolved_path.resolve()
    if not resolved_path.exists():
        raise WorkspacePathError(f"'{path}' does not exist.")

    try:
        return resolved_path.relative_to(workspace)
    except ValueError as error:
        raise WorkspacePathError(f"'{path}' is outside the workspace.") from error


def bazelignore_paths(workspace: Path) -> set[str]:
    """Return ignored workspace-relative paths from `.bazelignore`.

    Args:
        workspace: The Bazel workspace root.

    Returns:
        The ignored workspace-relative paths with trailing slashes removed.
    """
    ignored_file = workspace / ".bazelignore"
    if not ignored_file.is_file():
        return set()

    return {
        stripped.rstrip("/")
        for line in ignored_file.read_text(encoding="utf-8").splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    }


def iter_build_files(workspace: Path) -> Iterator[Path]:
    """Yield checked-in `BUILD.bazel` files for a workspace.

    Args:
        workspace: The Bazel workspace root.

    Yields:
        Non-ignored `BUILD.bazel` files, skipping symlinked directories.
    """
    ignored_paths = bazelignore_paths(workspace)

    def is_ignored(path: Path) -> bool:
        relative_path = path.relative_to(workspace).as_posix()
        if relative_path in ignored_paths:
            return True

        if any(relative_path.startswith(f"{ignored_path}/") for ignored_path in ignored_paths):
            return True

        first_component = path.relative_to(workspace).parts[0]
        return first_component in {
            "_tmp",
            "bazel-bin",
            "bazel-out",
            "bazel-testlogs",
            "external",
        } or first_component.startswith("bazel-")

    def walk(directory: Path) -> Iterator[Path]:
        build_file = directory / "BUILD.bazel"
        if build_file.is_file() and not is_ignored(build_file):
            yield build_file

        for child in directory.iterdir():
            if not child.is_dir() or child.is_symlink() or is_ignored(child):
                continue

            yield from walk(child)

    yield from walk(workspace)
