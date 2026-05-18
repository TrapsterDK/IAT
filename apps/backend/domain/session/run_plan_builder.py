"""Deterministic run-plan construction for one published IAT."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

from apps.backend.domain.session.exceptions import SessionConfigurationError
from apps.backend.models.plan import BlockPlan, PlannedStimulus, ResponseSide, RunPlan, TrialPlan

if TYPE_CHECKING:
    from apps.backend.models.catalog import CatalogIat


def build_run_plan(catalog_iat: CatalogIat, seed: int) -> RunPlan:
    """Build one deterministic seven-block IAT run plan.

    Args:
        catalog_iat: Catalog IAT definition used to build the runtime plan.
        seed: Deterministic random seed for per-block ordering.

    Returns:
        The constructed deterministic run plan.
    """
    first_pair_left, first_pair_right = catalog_iat.categories[0]
    second_pair_left, second_pair_right = catalog_iat.categories[1]
    block_layouts = (
        ((first_pair_left,), (first_pair_right,), True),
        ((second_pair_left,), (second_pair_right,), True),
        ((first_pair_left, second_pair_left), (first_pair_right, second_pair_right), True),
        ((first_pair_left, second_pair_left), (first_pair_right, second_pair_right), False),
        ((first_pair_right,), (first_pair_left,), True),
        ((first_pair_right, second_pair_left), (first_pair_left, second_pair_right), True),
        ((first_pair_right, second_pair_left), (first_pair_left, second_pair_right), False),
    )

    randomizer = Random(seed)
    built_blocks = []
    for left_categories, right_categories, is_practice in block_layouts:
        trial_candidates: list[tuple[PlannedStimulus, ResponseSide]] = [
            (
                PlannedStimulus(text=stimulus.text, image_path=stimulus.image_path),
                response_side,
            )
            for categories, response_side in (
                (left_categories, ResponseSide.LEFT),
                (right_categories, ResponseSide.RIGHT),
            )
            for category in categories
            for stimulus in category.stimuli
        ]

        randomizer.shuffle(trial_candidates)

        f, *r = left_categories
        left_labels = (f.label, r[0].label) if r else (f.label,)
        f, *r = right_categories
        right_labels = (f.label, r[0].label) if r else (f.label,)
        if len({*left_labels, *right_labels}) != len(left_labels) + len(right_labels):
            raise SessionConfigurationError("Session block labels must be unique within one deterministic block.")

        built_blocks.append(
            BlockPlan(
                left_labels=left_labels,
                right_labels=right_labels,
                is_practice=is_practice,
                trials=tuple(
                    TrialPlan(
                        stimulus=stimulus,
                        correct_response_side=correct_response_side,
                    )
                    for stimulus, correct_response_side in trial_candidates
                ),
            )
        )

    return RunPlan(blocks=tuple(built_blocks))
