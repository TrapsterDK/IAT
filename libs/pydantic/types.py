"""Shared Pydantic type aliases."""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
