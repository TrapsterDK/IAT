"""Tests for deterministic session run-plan construction."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from apps.backend.domain.iat.models import PublishedCategory, PublishedIat, PublishedStimulus
from apps.backend.domain.session.exceptions import SessionConfigurationError
from apps.backend.domain.session.models import BlockPlan, ResponseSide
from apps.backend.domain.session.run_plan_builder import build_run_plan


def _build_published_iat() -> PublishedIat:
    return PublishedIat(
        slug="sample-iat",
        title="Sample IAT",
        description="sample description",
        categories=(
            (
                PublishedCategory(
                    slug="alpha",
                    label="Alpha",
                    stimuli=(PublishedStimulus(text="alpha-1"), PublishedStimulus(text="alpha-2")),
                ),
                PublishedCategory(
                    slug="beta",
                    label="Beta",
                    stimuli=(PublishedStimulus(text="beta-1"), PublishedStimulus(text="beta-2")),
                ),
            ),
            (
                PublishedCategory(
                    slug="good",
                    label="Good",
                    stimuli=(PublishedStimulus(text="good-1"), PublishedStimulus(text="good-2")),
                ),
                PublishedCategory(
                    slug="bad",
                    label="Bad",
                    stimuli=(PublishedStimulus(text="bad-1"), PublishedStimulus(text="bad-2")),
                ),
            ),
        ),
    )


def _sorted_text_trial_pairs(block: BlockPlan) -> list[tuple[str | None, ResponseSide]]:
    return sorted((trial.stimulus.text, trial.correct_response_side) for trial in block.trials)


def test_build_run_plan_builds_expected_seven_block_layout() -> None:
    # Given: one published IAT with two category pairs and two stimuli per category.
    published_iat = _build_published_iat()

    # When: one deterministic run plan is generated.
    run_plan = build_run_plan(
        published_iat,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
        seed=123,
    )

    # Then: the generated plan keeps the expected IAT block layout and trial counts.
    assert run_plan.anticipation_threshold_ms == 300
    assert run_plan.response_timeout_ms == 10_000
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
    published_iat = _build_published_iat()

    # When: one deterministic run plan is generated.
    run_plan = build_run_plan(
        published_iat,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
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
    published_iat = _build_published_iat()

    # When: two plans are generated from the same seed.
    first_run_plan = build_run_plan(
        published_iat,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
        seed=99,
    )
    second_run_plan = build_run_plan(
        published_iat,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
        seed=99,
    )

    # Then: the per-block shuffled trial order stays deterministic.
    assert first_run_plan == second_run_plan


def test_build_run_plan_preserves_expected_trial_order_for_seed() -> None:
    # Given: one published IAT and one seed whose trial order is persisted and consumed downstream.
    published_iat = _build_published_iat()

    # When: one deterministic run plan is generated.
    run_plan = build_run_plan(
        published_iat,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
        seed=123,
    )

    # Then: the flattened trial execution order stays stable for that seed.
    assert [
        (trial.stimulus.text, trial.correct_response_side) for block in run_plan.blocks for trial in block.trials
    ] == [
        ("beta-1", ResponseSide.RIGHT),
        ("beta-2", ResponseSide.RIGHT),
        ("alpha-2", ResponseSide.LEFT),
        ("alpha-1", ResponseSide.LEFT),
        ("bad-1", ResponseSide.RIGHT),
        ("good-1", ResponseSide.LEFT),
        ("good-2", ResponseSide.LEFT),
        ("bad-2", ResponseSide.RIGHT),
        ("bad-1", ResponseSide.RIGHT),
        ("bad-2", ResponseSide.RIGHT),
        ("alpha-2", ResponseSide.LEFT),
        ("good-1", ResponseSide.LEFT),
        ("beta-2", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.RIGHT),
        ("good-2", ResponseSide.LEFT),
        ("alpha-1", ResponseSide.LEFT),
        ("bad-1", ResponseSide.RIGHT),
        ("alpha-1", ResponseSide.LEFT),
        ("good-2", ResponseSide.LEFT),
        ("beta-2", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.RIGHT),
        ("bad-2", ResponseSide.RIGHT),
        ("alpha-2", ResponseSide.LEFT),
        ("good-1", ResponseSide.LEFT),
        ("alpha-1", ResponseSide.RIGHT),
        ("alpha-2", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.LEFT),
        ("beta-2", ResponseSide.LEFT),
        ("alpha-2", ResponseSide.RIGHT),
        ("good-1", ResponseSide.LEFT),
        ("bad-2", ResponseSide.RIGHT),
        ("bad-1", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.LEFT),
        ("good-2", ResponseSide.LEFT),
        ("alpha-1", ResponseSide.RIGHT),
        ("beta-2", ResponseSide.LEFT),
        ("good-1", ResponseSide.LEFT),
        ("good-2", ResponseSide.LEFT),
        ("alpha-2", ResponseSide.RIGHT),
        ("alpha-1", ResponseSide.RIGHT),
        ("bad-2", ResponseSide.RIGHT),
        ("bad-1", ResponseSide.RIGHT),
        ("beta-1", ResponseSide.LEFT),
        ("beta-2", ResponseSide.LEFT),
    ]


def test_build_run_plan_keeps_published_image_paths_in_trials() -> None:
    # Given: one published IAT containing one image stimulus.
    published_iat = PublishedIat(
        slug="sample-iat",
        title="Sample IAT",
        description="sample description",
        categories=(
            (
                PublishedCategory(
                    slug="alpha",
                    label="Alpha",
                    stimuli=(PublishedStimulus(image_path=PurePosixPath("sample-iat/alpha/example.png")),),
                ),
                PublishedCategory(
                    slug="beta",
                    label="Beta",
                    stimuli=(PublishedStimulus(text="beta"),),
                ),
            ),
            (
                PublishedCategory(
                    slug="good",
                    label="Good",
                    stimuli=(PublishedStimulus(text="good"),),
                ),
                PublishedCategory(
                    slug="bad",
                    label="Bad",
                    stimuli=(PublishedStimulus(text="bad"),),
                ),
            ),
        ),
    )

    # When: one deterministic run plan is built.
    run_plan = build_run_plan(
        published_iat,
        anticipation_threshold_ms=300,
        response_timeout_ms=10_000,
        seed=123,
    )

    # Then: image-backed trials keep the published stimulus path instead of one routed URL.
    image_trials = [
        trial for block in run_plan.blocks for trial in block.trials if trial.stimulus.image_path is not None
    ]
    assert image_trials
    assert {trial.stimulus.image_path for trial in image_trials} == {PurePosixPath("sample-iat/alpha/example.png")}


@pytest.mark.parametrize(
    ("anticipation_threshold_ms", "response_timeout_ms"),
    [
        pytest.param(-1, 10_000, id="negative_anticipation_threshold"),
        pytest.param(300, 0, id="non_positive_response_timeout"),
        pytest.param(300, 300, id="equal_thresholds"),
        pytest.param(301, 300, id="anticipation_after_timeout"),
    ],
)
def test_build_run_plan_rejects_invalid_timing_configuration(
    anticipation_threshold_ms: int,
    response_timeout_ms: int,
) -> None:
    # Given: one published IAT and one invalid timing configuration.
    published_iat = _build_published_iat()

    # When: one deterministic run plan is generated.
    # Then: the builder rejects timing that cannot produce one valid session plan.
    with pytest.raises(
        SessionConfigurationError,
        match="Session anticipation thresholds must be lower than response timeouts",
    ):
        build_run_plan(
            published_iat,
            anticipation_threshold_ms=anticipation_threshold_ms,
            response_timeout_ms=response_timeout_ms,
            seed=123,
        )
