"""Shared internal models for scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.backend.models.plan import ResponseSide
    from apps.backend.models.session import TrialEventType


@dataclass(frozen=True, slots=True)
class SessionScoringEvent:
    """One persisted participant action within one completed trial."""

    event_type: TrialEventType
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class SessionScoringTrial:
    """One completed trial reconstructed from one persisted session."""

    correct_response_side: ResponseSide
    events: tuple[SessionScoringEvent, ...]


@dataclass(frozen=True, slots=True)
class SessionScoringBlock:
    """One completed session block with its persisted labels and trials."""

    left_labels: tuple[str, ...]
    right_labels: tuple[str, ...]
    is_practice: bool
    trials: tuple[SessionScoringTrial, ...]


@dataclass(frozen=True, slots=True)
class CompletedSessionSnapshot:
    """Full persisted completed-session state needed for scoring."""

    blocks: tuple[SessionScoringBlock, ...]


@dataclass(frozen=True, slots=True)
class SessionScoreResult:
    """One computed session D-score with one user-facing headline."""

    d_score: float
    headline: str
