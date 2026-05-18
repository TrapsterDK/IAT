"""Shared internal models for runtime state and uploads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class TrialEventType(StrEnum):
    """Primitive participant actions captured while one trial is active."""

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class ClientContext:
    """Non-identifying client metadata stored for later analysis."""

    user_agent: str | None = None
    platform: str | None = None
    viewport_width_px: int | None = None
    viewport_height_px: int | None = None
    device_pixel_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class SessionCreateInput:
    """Typed session-creation payload passed beyond the API boundary."""

    iat_slug: str
    client_context: ClientContext


@dataclass(frozen=True, slots=True)
class SessionState:
    """Mutable session lifecycle metadata stored on the session root row."""

    session_id: int
    session_key: str
    created_at_utc: datetime
    completed_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class TrialEventInput:
    """One typed raw participant action before completion semantics are validated."""

    event_type: TrialEventType
    elapsed_ms: int


@dataclass(frozen=True, slots=True)
class CompletedTrialInput:
    """One typed raw completed-trial payload before completion semantics are validated."""

    events: tuple[TrialEventInput, ...]


@dataclass(frozen=True, slots=True)
class CompletedBlockInput:
    """One typed raw completed-block payload before completion semantics are validated."""

    trials: tuple[CompletedTrialInput, ...]
