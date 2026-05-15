"""Tests for shared Pydantic type aliases."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from libs.pydantic.types import AbsoluteDirectoryPath, AbsoluteFilePath, AbsolutePath, UniqueHashable, UniqueUnhashable


def test_absolute_path_accepts_absolute_path(tmp_path: Path) -> None:
    # Given: one absolute path value.
    absolute_path = tmp_path / "resource"

    # When: the absolute path type validates the path.
    validated_path = TypeAdapter(AbsolutePath).validate_python(absolute_path)

    # Then: the absolute path is accepted without existence checks.
    assert validated_path == absolute_path


def test_absolute_path_rejects_relative_path() -> None:
    # Given: one relative path value.
    relative_path = Path("resource")

    # When: the absolute path type validates the path.
    # Then: the relative path is rejected before any file-system checks.
    with pytest.raises(ValidationError, match="Path must be absolute"):
        TypeAdapter(AbsolutePath).validate_python(relative_path)


def test_absolute_directory_path_accepts_absolute_existing_directory(tmp_path: Path) -> None:
    # Given: one absolute existing directory path.
    directory_path = tmp_path / "resources"
    directory_path.mkdir(parents=True, exist_ok=True)

    # When: the absolute directory type validates the path.
    validated_path = TypeAdapter(AbsoluteDirectoryPath).validate_python(directory_path)

    # Then: the directory path is accepted.
    assert validated_path == directory_path


def test_absolute_directory_path_rejects_relative_existing_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: one relative path that points to one existing directory from the current working directory.
    directory_path = tmp_path / "resources"
    directory_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    # When: the absolute directory type validates the relative path.
    # Then: the relative directory path is rejected.
    with pytest.raises(ValidationError, match="Path must be absolute"):
        TypeAdapter(AbsoluteDirectoryPath).validate_python(Path("resources"))


def test_absolute_file_path_accepts_absolute_existing_file(tmp_path: Path) -> None:
    # Given: one absolute existing file path.
    file_path = tmp_path / "config.yaml"
    file_path.write_text("name: config\n", encoding="utf-8")

    # When: the absolute file type validates the path.
    validated_path = TypeAdapter(AbsoluteFilePath).validate_python(file_path)

    # Then: the file path is accepted.
    assert validated_path == file_path


def test_absolute_file_path_rejects_relative_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: one relative path that points to one existing file from the current working directory.
    file_path = tmp_path / "config.yaml"
    file_path.write_text("name: config\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    # When: the absolute file type validates the relative path.
    # Then: the relative file path is rejected.
    with pytest.raises(ValidationError, match="Path must be absolute"):
        TypeAdapter(AbsoluteFilePath).validate_python(Path("config.yaml"))


def test_absolute_directory_path_rejects_absolute_missing_directory(tmp_path: Path) -> None:
    # Given: one absolute path that does not point to an existing directory.
    missing_directory_path = tmp_path / "missing"

    # When: the absolute directory type validates the path.
    # Then: the missing directory path is rejected by the directory-path validator.
    with pytest.raises(ValidationError, match="Path does not point to a directory"):
        TypeAdapter(AbsoluteDirectoryPath).validate_python(missing_directory_path)


def test_absolute_file_path_rejects_absolute_missing_file(tmp_path: Path) -> None:
    # Given: one absolute path that does not point to an existing file.
    missing_file_path = tmp_path / "missing.yaml"

    # When: the absolute file type validates the path.
    # Then: the missing file path is rejected by the file-path validator.
    with pytest.raises(ValidationError, match="Path does not point to a file"):
        TypeAdapter(AbsoluteFilePath).validate_python(missing_file_path)


@pytest.mark.parametrize(
    ("unique_type", "values"),
    [
        pytest.param(UniqueHashable[list[int]], [1, 2, 3], id="list"),
        pytest.param(
            UniqueHashable[tuple[Path, ...]],
            (Path("alpha.yaml"), Path("bravo.yaml")),
            id="tuple_variadic",
        ),
        pytest.param(
            UniqueHashable[tuple[Path, Path]],
            (Path("alpha.yaml"), Path("bravo.yaml")),
            id="tuple_fixed_two",
        ),
        pytest.param(
            UniqueHashable[tuple[Path, Path, Path]],
            (Path("alpha.yaml"), Path("bravo.yaml"), Path("charlie.yaml")),
            id="tuple_fixed_three",
        ),
    ],
)
def test_unique_accepts_distinct_values(unique_type: object, values: object) -> None:
    # Given: one unique collection type and one distinct collection value.
    adapter = TypeAdapter(unique_type)

    # When: the unique type validates the value.
    validated_values = adapter.validate_python(values)

    # Then: the distinct collection is accepted unchanged.
    assert validated_values == values


@pytest.mark.parametrize(
    ("unique_type", "values"),
    [
        pytest.param(UniqueHashable[list[int]], [1, 1, 2], id="list"),
        pytest.param(
            UniqueHashable[tuple[Path, ...]],
            (Path("alpha.yaml"), Path("alpha.yaml")),
            id="tuple_variadic",
        ),
        pytest.param(
            UniqueHashable[tuple[Path, Path]],
            (Path("alpha.yaml"), Path("alpha.yaml")),
            id="tuple_fixed_two",
        ),
        pytest.param(
            UniqueHashable[tuple[Path, Path, Path]],
            (Path("alpha.yaml"), Path("bravo.yaml"), Path("alpha.yaml")),
            id="tuple_fixed_three",
        ),
    ],
)
def test_unique_rejects_duplicate_values(unique_type: object, values: object) -> None:
    # Given: one unique collection type and one collection value with duplicates.
    adapter = TypeAdapter(unique_type)

    # When: the unique type validates the value.
    # Then: duplicate values are rejected.
    with pytest.raises(ValidationError, match="Collection items must be unique"):
        adapter.validate_python(values)


def test_unique_rejects_unhashable_values() -> None:
    # Given: one unique collection type and one collection value with unhashable items.
    adapter = TypeAdapter(UniqueHashable[list[dict[str, str]]])

    # When: the unique type validates the value.
    # Then: unhashable items are rejected by the uniqueness implementation.
    with pytest.raises(TypeError, match="Collection items must be hashable"):
        adapter.validate_python([{"slug": "alpha"}, {"slug": "alpha"}])


@pytest.mark.parametrize(
    ("unique_type", "values"),
    [
        pytest.param(
            UniqueUnhashable[list[dict[str, str]]],
            [{"slug": "alpha"}, {"slug": "bravo"}],
            id="list_unhashable",
        ),
        pytest.param(
            UniqueUnhashable[tuple[dict[str, str], dict[str, str]]],
            ({"slug": "alpha"}, {"slug": "bravo"}),
            id="tuple_fixed_unhashable",
        ),
        pytest.param(
            UniqueUnhashable[list[int]],
            [1, 2, 3],
            id="list_hashable",
        ),
    ],
)
def test_unique_unhashable_accepts_distinct_values(unique_type: object, values: object) -> None:
    # Given: one unique-unhashable collection type and one distinct collection value.
    adapter = TypeAdapter(unique_type)

    # When: the unique-unhashable type validates the value.
    validated_values = adapter.validate_python(values)

    # Then: the distinct collection is accepted unchanged.
    assert validated_values == values


@pytest.mark.parametrize(
    ("unique_type", "values"),
    [
        pytest.param(
            UniqueUnhashable[list[dict[str, str]]],
            [{"slug": "alpha"}, {"slug": "alpha"}],
            id="list_unhashable",
        ),
        pytest.param(
            UniqueUnhashable[tuple[dict[str, str], dict[str, str]]],
            ({"slug": "alpha"}, {"slug": "alpha"}),
            id="tuple_fixed_unhashable",
        ),
        pytest.param(
            UniqueUnhashable[list[int]],
            [1, 1, 2],
            id="list_hashable",
        ),
    ],
)
def test_unique_unhashable_rejects_duplicate_values(unique_type: object, values: object) -> None:
    # Given: one unique-unhashable collection type and one collection value with duplicates.
    adapter = TypeAdapter(unique_type)

    # When: the unique-unhashable type validates the value.
    # Then: duplicate values are rejected.
    with pytest.raises(ValidationError, match="Collection items must be unique"):
        adapter.validate_python(values)
