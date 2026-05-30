"""Typed CSV helpers for offline analysis artifacts."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from libs.config.config import ConfigModel

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def read_csv[T: ConfigModel](input_path: Path, row_type: type[T]) -> list[T]:
    """Read a CSV file into validated row models.

    Args:
        input_path: CSV file path to read.
        row_type: Row model type used for validation.

    Returns:
        Validated rows in file order.
    """
    with input_path.open(newline="", encoding="utf-8") as input_file:
        return [row_type.model_validate(dict(row)) for row in csv.DictReader(input_file)]


def write_csv[T: ConfigModel](output_path: Path, row_type: type[T], rows: Iterable[T]) -> None:
    """Write validated row models to a CSV file.

    Args:
        output_path: CSV file path to write.
        row_type: Row model type defining CSV columns.
        rows: Rows to serialize.
    """
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=tuple(row_type.model_fields))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump(mode="json"))
