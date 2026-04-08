"""Attempt scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import TYPE_CHECKING

from backend.app.models import ResponseSide

if TYPE_CHECKING:
    from backend.app.models import Attempt, Phase, Showing


@dataclass(frozen=True)
class AttemptScoreSummary:
    """Aggregate score summary for one completed attempt."""

    showing_count: int
    accuracy: float
    mean_initial_reaction_time_ms: float
    mean_completed_reaction_time_ms: float


def _expected_side_for_showing(showing: Showing) -> ResponseSide | None:
    phase: Phase = showing.phase
    stimulus_category_id = showing.stimulus.category_id
    left_category_ids = {phase.left_primary_category_id}
    right_category_ids = {phase.right_primary_category_id}
    if phase.left_secondary_category_id is not None:
        left_category_ids.add(phase.left_secondary_category_id)
    if phase.right_secondary_category_id is not None:
        right_category_ids.add(phase.right_secondary_category_id)

    if stimulus_category_id in left_category_ids:
        return ResponseSide.LEFT
    if stimulus_category_id in right_category_ids:
        return ResponseSide.RIGHT
    return None


def _initial_reaction_time_ms(showing: Showing) -> float:
    return showing.inputs[0].handler_timestamp_ms - showing.stimulus_onset_ms


def _completed_reaction_time_ms(showing: Showing) -> float:
    return showing.inputs[-1].handler_timestamp_ms - showing.stimulus_onset_ms


def _is_correct(showing: Showing) -> bool:
    expected_side = _expected_side_for_showing(showing)
    if expected_side is None:
        return False
    return showing.inputs[-1].side == expected_side and len(showing.inputs) == 1


def score_attempt(attempt: Attempt) -> AttemptScoreSummary:
    """Compute summary metrics for a completed attempt."""
    if not attempt.showings:
        return AttemptScoreSummary(
            showing_count=0,
            accuracy=0.0,
            mean_initial_reaction_time_ms=0.0,
            mean_completed_reaction_time_ms=0.0,
        )

    initial_rts = [_initial_reaction_time_ms(showing) for showing in attempt.showings]
    completed_rts = [_completed_reaction_time_ms(showing) for showing in attempt.showings]
    correct_showings = sum(1 for showing in attempt.showings if _is_correct(showing))

    return AttemptScoreSummary(
        showing_count=len(attempt.showings),
        accuracy=round(correct_showings / len(attempt.showings), 4),
        mean_initial_reaction_time_ms=round(fmean(initial_rts), 2),
        mean_completed_reaction_time_ms=round(fmean(completed_rts), 2),
    )
