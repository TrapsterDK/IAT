"""Shared internal models for deterministic run plans."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import PurePosixPath

type BlockLabels = tuple[str] | tuple[str, str]


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

    blocks: tuple[BlockPlan, ...]
