"""Tests for deterministic session run-plan construction."""

from __future__ import annotations

from pathlib import PurePosixPath

from apps.backend.domain.session.run_plan_builder import build_run_plan
from apps.backend.models.catalog import CatalogCategory, CatalogIat, CatalogStimulus
from apps.backend.models.plan import BlockPlan, ResponseSide


def _build_catalog_iat() -> CatalogIat:
    return CatalogIat(
        slug="sample-iat",
        title="Sample IAT",
        description="sample description",
        categories=(
            (
                CatalogCategory(
                    slug="alpha",
                    label="Alpha",
                    stimuli=(CatalogStimulus(text="alpha-1"), CatalogStimulus(text="alpha-2")),
                ),
                CatalogCategory(
                    slug="beta",
                    label="Beta",
                    stimuli=(CatalogStimulus(text="beta-1"), CatalogStimulus(text="beta-2")),
                ),
            ),
            (
                CatalogCategory(
                    slug="good",
                    label="Good",
                    stimuli=(CatalogStimulus(text="good-1"), CatalogStimulus(text="good-2")),
                ),
                CatalogCategory(
                    slug="bad",
                    label="Bad",
                    stimuli=(CatalogStimulus(text="bad-1"), CatalogStimulus(text="bad-2")),
                ),
            ),
        ),
    )


def _sorted_text_trial_pairs(block: BlockPlan) -> list[tuple[str | None, ResponseSide]]:
    return sorted((trial.stimulus.text, trial.correct_response_side) for trial in block.trials)


def test_build_run_plan_builds_expected_seven_block_layout() -> None:
    # Given: one published IAT with two category pairs and two stimuli per category.
    catalog_iat = _build_catalog_iat()

    # When: one deterministic run plan is generated.
    run_plan = build_run_plan(
        catalog_iat,
        seed=123,
    )

    # Then: the generated plan keeps the expected IAT block layout and trial counts.
    assert [block.left_labels for block in run_plan.blocks] == [
        ("Alpha",),
        ("Good",),
        ("Alpha", "Good"),
        ("Alpha", "Good"),
        ("Beta",),
        ("Beta", "Good"),
        ("Beta", "Good"),
    ]
    assert [block.right_labels for block in run_plan.blocks] == [
        ("Beta",),
        ("Bad",),
        ("Beta", "Bad"),
        ("Beta", "Bad"),
        ("Alpha",),
        ("Alpha", "Bad"),
        ("Alpha", "Bad"),
    ]
    assert [block.is_practice for block in run_plan.blocks] == [True, True, True, False, True, True, False]
    assert [len(block.trials) for block in run_plan.blocks] == [4, 4, 8, 8, 4, 8, 8]


def test_build_run_plan_populates_expected_trials_in_representative_blocks() -> None:
    # Given: one published IAT with distinct text stimuli in each category.
    catalog_iat = _build_catalog_iat()

    # When: one deterministic run plan is generated.
    run_plan = build_run_plan(
        catalog_iat,
        seed=123,
    )

    # Then: representative blocks contain the expected stimuli on the expected response side, regardless of shuffle order.
    assert _sorted_text_trial_pairs(run_plan.blocks[0]) == [
        ("alpha-1", ResponseSide.LEFT),
        ("alpha-2", ResponseSide.LEFT),
        ("beta-1", ResponseSide.RIGHT),
        ("beta-2", ResponseSide.RIGHT),
    ]
    assert _sorted_text_trial_pairs(run_plan.blocks[2]) == [
        ("alpha-1", ResponseSide.LEFT),
        ("alpha-2", ResponseSide.LEFT),
        ("bad-1", ResponseSide.RIGHT),
        ("bad-2", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.RIGHT),
        ("beta-2", ResponseSide.RIGHT),
        ("good-1", ResponseSide.LEFT),
        ("good-2", ResponseSide.LEFT),
    ]
    assert _sorted_text_trial_pairs(run_plan.blocks[4]) == [
        ("alpha-1", ResponseSide.RIGHT),
        ("alpha-2", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.LEFT),
        ("beta-2", ResponseSide.LEFT),
    ]
    assert _sorted_text_trial_pairs(run_plan.blocks[5]) == [
        ("alpha-1", ResponseSide.RIGHT),
        ("alpha-2", ResponseSide.RIGHT),
        ("bad-1", ResponseSide.RIGHT),
        ("bad-2", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.LEFT),
        ("beta-2", ResponseSide.LEFT),
        ("good-1", ResponseSide.LEFT),
        ("good-2", ResponseSide.LEFT),
    ]


def test_build_run_plan_keeps_shuffle_order_stable_for_one_seed() -> None:
    # Given: one published IAT and one fixed deterministic seed.
    catalog_iat = _build_catalog_iat()

    # When: two plans are generated from the same seed.
    first_run_plan = build_run_plan(
        catalog_iat,
        seed=99,
    )
    second_run_plan = build_run_plan(
        catalog_iat,
        seed=99,
    )

    # Then: the per-block shuffled trial order stays deterministic.
    assert first_run_plan == second_run_plan


def test_build_run_plan_preserves_representative_block_order_for_seed() -> None:
    # Given: one published IAT and one seed whose block order is persisted and consumed downstream.
    catalog_iat = _build_catalog_iat()

    # When: one deterministic run plan is generated.
    run_plan = build_run_plan(
        catalog_iat,
        seed=123,
    )

    # Then: one representative block keeps one stable execution order for that seed.
    assert [(trial.stimulus.text, trial.correct_response_side) for trial in run_plan.blocks[2].trials] == [
        ("bad-1", ResponseSide.RIGHT),
        ("bad-2", ResponseSide.RIGHT),
        ("alpha-2", ResponseSide.LEFT),
        ("good-1", ResponseSide.LEFT),
        ("beta-2", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.RIGHT),
        ("good-2", ResponseSide.LEFT),
        ("alpha-1", ResponseSide.LEFT),
    ]


def test_build_run_plan_keeps_published_image_paths_in_trials() -> None:
    # Given: one published IAT containing one image stimulus.
    catalog_iat = CatalogIat(
        slug="sample-iat",
        title="Sample IAT",
        description="sample description",
        categories=(
            (
                CatalogCategory(
                    slug="alpha",
                    label="Alpha",
                    stimuli=(CatalogStimulus(image_path=PurePosixPath("sample-iat/alpha/example.png")),),
                ),
                CatalogCategory(
                    slug="beta",
                    label="Beta",
                    stimuli=(CatalogStimulus(text="beta"),),
                ),
            ),
            (
                CatalogCategory(
                    slug="good",
                    label="Good",
                    stimuli=(CatalogStimulus(text="good"),),
                ),
                CatalogCategory(
                    slug="bad",
                    label="Bad",
                    stimuli=(CatalogStimulus(text="bad"),),
                ),
            ),
        ),
    )

    # When: one deterministic run plan is built.
    run_plan = build_run_plan(
        catalog_iat,
        seed=123,
    )

    # Then: image-backed trials keep the published stimulus path instead of one routed URL.
    image_trials = [
        trial for block in run_plan.blocks for trial in block.trials if trial.stimulus.image_path is not None
    ]
    assert image_trials
    assert {trial.stimulus.image_path for trial in image_trials} == {PurePosixPath("sample-iat/alpha/example.png")}
