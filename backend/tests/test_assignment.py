"""Tests for deterministic variant assignment."""

from backend.app.models import ExperimentVariant
from backend.app.services.assignment import assign_variant, build_session_seed


def test_assign_variant_is_deterministic() -> None:
    """The same assignment key should always select the same variant."""
    variants = [
        ExperimentVariant(
            key_event_mode="keyup",
            preload_assets=False,
            inter_trial_interval_ms=250,
            response_timeout_ms=5000,
        ),
        ExperimentVariant(
            key_event_mode="keydown",
            preload_assets=True,
            inter_trial_interval_ms=150,
            response_timeout_ms=5000,
        ),
    ]

    first = assign_variant(variants, "session-a")
    second = assign_variant(variants, "session-a")

    if first is not second:
        msg = "Expected deterministic variant assignment for identical keys."
        raise AssertionError(msg)


def test_build_session_seed_is_stable() -> None:
    """The same public id should always produce the same RNG seed."""
    if build_session_seed("session-a") != build_session_seed("session-a"):
        msg = "Expected stable session seed generation."
        raise AssertionError(msg)
