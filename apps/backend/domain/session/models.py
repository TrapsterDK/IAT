"""Plain internal domain models for persisted IAT execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import PurePosixPath

type BlockLabels = tuple[str] | tuple[str, str]


class TrialEventType(StrEnum):
    """Primitive participant actions captured while one trial is active."""

    LEFT = "left"
    RIGHT = "right"
    TIMEOUT = "timeout"


class ResponseSide(StrEnum):
    """Participant-facing response side recorded for one trial."""

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class PlannedStimulus:
    """One public text or image stimulus in a run plan."""

    text: str | None = None
    image_path: PurePosixPath | None = None


@dataclass(frozen=True, slots=True)
class TrialPlan:
    """One executable trial in one deterministic IAT run plan."""

    stimulus: PlannedStimulus
    correct_response_side: ResponseSide


@dataclass(frozen=True, slots=True)
class BlockPlan:
    """One block in one deterministic IAT run plan."""

    left_labels: BlockLabels
    right_labels: BlockLabels
    is_practice: bool
    trials: tuple[TrialPlan, ...]


@dataclass(frozen=True, slots=True)
class RunPlan:
    """One immutable deterministic IAT plan served to one client session."""

    anticipation_threshold_ms: int
    response_timeout_ms: int
    blocks: tuple[BlockPlan, ...]


@dataclass(frozen=True, slots=True)
class ClientContext:
    """Non-identifying client metadata stored for later analysis."""

    user_agent: str | None = None
    platform: str | None = None
    viewport_width_px: int | None = None
    viewport_height_px: int | None = None
    device_pixel_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class TrialEvent:
    """One primitive event captured for one trial in one client session."""

    trial_id: int
    event_index: int
    elapsed_ms: int
    event_type: TrialEventType


@dataclass(frozen=True, slots=True)
class SessionState:
    """Mutable session lifecycle metadata stored on the session root row."""

    session_id: int
    session_key: str
    created_at_utc: datetime
    completed_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class SessionUploadState:
    """Validated session upload state reconstructed from persisted data."""

    session_id: int
    completed_at_utc: datetime | None
    block_trial_counts: tuple[int, ...]
    next_trial_id: int
    next_block_index: int
    next_event_index: int
    anticipation_threshold_ms: int
    response_timeout_ms: int


@dataclass(frozen=True, slots=True)
class TrialEventUploadInput:
    """One typed raw participant action before upload semantics are validated."""

    event_type: TrialEventType
    elapsed_ms: int


@dataclass(frozen=True, slots=True)
class TrialUploadInput:
    """One typed raw trial payload before upload semantics are validated."""

    events: tuple[TrialEventUploadInput, ...]


@dataclass(frozen=True, slots=True)
class BlockUploadInput:
    """One typed raw block payload before upload semantics are validated."""

    trials: tuple[TrialUploadInput, ...]


@dataclass(frozen=True, slots=True)
class BlockUpload:
    """One validated block upload ready to be persisted."""

    session_id: int
    trial_events: tuple[TrialEvent, ...]
    completes_session: bool
