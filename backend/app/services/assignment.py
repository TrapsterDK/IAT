"""Variant assignment helpers."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from backend.app.models import ExperimentVariant


def _digest_value(seed_text: str) -> int:
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def assign_variant(variants: Sequence[ExperimentVariant], assignment_key: str) -> ExperimentVariant:
    """Deterministically assign a variant for a session key."""
    if not variants:
        msg = "No experiment variants are available."
        raise ValueError(msg)

    index = _digest_value(assignment_key) % len(variants)
    return variants[index]


def build_session_seed(public_id: str) -> int:
    """Build a deterministic RNG seed from a public session identifier."""
    return _digest_value(public_id) % 2_147_483_647
