"""Serialization helpers for browser-facing test payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.schemas import (
    AttemptSummaryPayload,
    CategorySummary,
    PhaseCategorySummary,
    PhaseSideCategories,
    PhaseSummary,
    StimulusSummary,
    TestPayload,
    TestSummaryPayload,
    VariantSummaryPayload,
)
from backend.app.services.assignment import build_session_seed

if TYPE_CHECKING:
    from backend.app.models import Experiment, ExperimentVariant, Phase, Stimulus


def _test_stimuli(test: Experiment) -> list[Stimulus]:
    return sorted(
        (stimulus for category in test.categories for stimulus in category.stimuli),
        key=lambda item: (item.category_id, item.id),
    )


def _phase_categories(phase: Phase) -> PhaseSideCategories:
    left_categories = [phase.left_primary_category]
    right_categories = [phase.right_primary_category]

    if phase.left_secondary_category is not None:
        left_categories.append(phase.left_secondary_category)
    if phase.right_secondary_category is not None:
        right_categories.append(phase.right_secondary_category)

    return PhaseSideCategories(
        left=[PhaseCategorySummary(id=category.id, label=category.label) for category in left_categories],
        right=[PhaseCategorySummary(id=category.id, label=category.label) for category in right_categories],
    )


def build_test_payload(
    test: Experiment,
    variant: ExperimentVariant,
    public_id: str,
    attempt_token: str,
) -> TestPayload:
    """Build the JSON payload needed to execute a test attempt in the browser."""
    categories = [
        CategorySummary(
            id=category.id,
            code=category.code,
            label=category.label,
        )
        for category in test.categories
    ]

    stimuli_by_category: dict[str, list[StimulusSummary]] = {}
    for stimulus in _test_stimuli(test):
        stimuli_by_category.setdefault(str(stimulus.category_id), []).append(
            StimulusSummary(
                id=stimulus.id,
                contentType="text" if stimulus.text_value is not None else "image",
                textValue=stimulus.text_value,
                assetPath=stimulus.asset_path,
            )
        )

    phases = [
        PhaseSummary(
            id=phase.id,
            sequenceNumber=phase.sequence_number,
            showingsPerCategory=phase.showings_per_category,
            categories=_phase_categories(phase),
        )
        for phase in test.phases
    ]

    return TestPayload(
        attempt=AttemptSummaryPayload(
            publicId=public_id,
            seed=build_session_seed(public_id),
            attemptToken=attempt_token,
        ),
        test=TestSummaryPayload(
            slug=test.slug,
            title=test.title,
            description=test.description,
        ),
        variant=VariantSummaryPayload(
            keyEventMode=variant.key_event_mode.value,
            keyboardShortcuts={"left": "E", "right": "I"},
            preloadAssets=variant.preload_assets,
            interTrialIntervalMs=variant.inter_trial_interval_ms,
            responseTimeoutMs=variant.response_timeout_ms,
        ),
        categories=categories,
        stimuliByCategory=stimuli_by_category,
        phases=phases,
    )
