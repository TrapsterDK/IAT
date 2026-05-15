"""Tests for typed IAT spec loading and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from apps.backend.iat_spec import IatSpec
from libs.testing.io import write_json, write_png

if TYPE_CHECKING:
    from pathlib import Path


def test_iat_spec_loads_valid_yaml_file(tmp_path: Path) -> None:
    # Given: one valid IAT spec file written in YAML.
    spec_path = tmp_path / "valid-spec.yaml"
    write_json(
        spec_path,
        {
            "slug": "age-attitudes",
            "title": "Age Attitudes IAT",
            "description": "Measures associations about age.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "young",
                            "label": "Young",
                            "stimuli": [{"text": "youth"}],
                        },
                        {
                            "slug": "old",
                            "label": "Old",
                            "stimuli": [{"text": "elder"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "pleasant",
                            "label": "Pleasant",
                            "stimuli": [{"text": "joy"}],
                        },
                        {
                            "slug": "unpleasant",
                            "label": "Unpleasant",
                            "stimuli": [{"text": "pain"}],
                        },
                    ]
                },
            ],
        },
    )

    # When: the spec is loaded through the typed model.
    resolved_spec = IatSpec.from_yaml_file(spec_path)

    # Then: the YAML file validates and keeps the expected slug.
    assert resolved_spec.slug == "age-attitudes"


def test_iat_spec_coerces_yaml_lists_to_tuples(tmp_path: Path) -> None:
    # Given: one spec file written with YAML lists for category pairs, categories, and stimuli.
    spec_path = tmp_path / "tuple-shape.yaml"
    write_json(
        spec_path,
        {
            "slug": "tuple-shape",
            "title": "Tuple Shape",
            "description": "Ensure fixed-length tuple fields still accept YAML lists.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "alpha",
                            "label": "Alpha",
                            "stimuli": [{"text": "one"}],
                        },
                        {
                            "slug": "beta",
                            "label": "Beta",
                            "stimuli": [{"text": "two"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "gamma",
                            "label": "Gamma",
                            "stimuli": [{"text": "three"}],
                        },
                        {
                            "slug": "delta",
                            "label": "Delta",
                            "stimuli": [{"text": "four"}],
                        },
                    ]
                },
            ],
        },
    )

    # When: the spec is loaded through the typed model.
    resolved_spec = IatSpec.from_yaml_file(spec_path)

    # Then: the list-shaped input still validates successfully.
    assert resolved_spec.slug == "tuple-shape"


def test_iat_spec_is_frozen_after_loading(tmp_path: Path) -> None:
    # Given: one valid IAT spec file written in YAML.
    spec_path = tmp_path / "valid-spec.yaml"
    write_json(
        spec_path,
        {
            "slug": "age-attitudes",
            "title": "Age Attitudes IAT",
            "description": "Measures associations about age.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "young",
                            "label": "Young",
                            "stimuli": [{"text": "youth"}],
                        },
                        {
                            "slug": "old",
                            "label": "Old",
                            "stimuli": [{"text": "elder"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "pleasant",
                            "label": "Pleasant",
                            "stimuli": [{"text": "joy"}],
                        },
                        {
                            "slug": "unpleasant",
                            "label": "Unpleasant",
                            "stimuli": [{"text": "pain"}],
                        },
                    ]
                },
            ],
        },
    )
    resolved_spec = IatSpec.from_yaml_file(spec_path)

    # When: one top-level field is reassigned after loading.
    # Then: the frozen spec model rejects mutation.
    with pytest.raises(ValidationError, match="Instance is frozen"):
        resolved_spec.slug = "changed"


def test_iat_spec_resolve_returns_absolute_png_paths(tmp_path: Path) -> None:
    # Given: one valid IAT spec that references one relative PNG file.
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    image_path = tmp_path / "resources/stimuli/face/example/images/seed-0.png"
    write_png(image_path)
    write_json(
        spec_path,
        {
            "slug": "sample-iat",
            "title": "Sample IAT",
            "description": "Measures one sample association.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "alpha",
                            "label": "Alpha",
                            "stimuli": [{"image": "../stimuli/face/example/images/seed-0.png"}],
                        },
                        {
                            "slug": "beta",
                            "label": "Beta",
                            "stimuli": [{"text": "beta"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "gamma",
                            "label": "Gamma",
                            "stimuli": [{"text": "gamma"}],
                        },
                        {
                            "slug": "delta",
                            "label": "Delta",
                            "stimuli": [{"text": "delta"}],
                        },
                    ]
                },
            ],
        },
    )
    raw_spec = IatSpec.from_yaml_file(spec_path)

    # When: the spec resolves its image paths against the spec directory.
    resolved_spec = raw_spec.resolve(spec_path.parent)

    # Then: the image path becomes one absolute file path.
    assert resolved_spec.categories[0].category[0].stimuli[0].image == image_path


def test_iat_spec_resolve_rejects_missing_image_files(tmp_path: Path) -> None:
    # Given: one valid IAT spec that references one PNG file that does not exist.
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    write_json(
        spec_path,
        {
            "slug": "sample-iat",
            "title": "Sample IAT",
            "description": "Measures one sample association.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "alpha",
                            "label": "Alpha",
                            "stimuli": [{"image": "../stimuli/face/example/images/seed-0.png"}],
                        },
                        {
                            "slug": "beta",
                            "label": "Beta",
                            "stimuli": [{"text": "beta"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "gamma",
                            "label": "Gamma",
                            "stimuli": [{"text": "gamma"}],
                        },
                        {
                            "slug": "delta",
                            "label": "Delta",
                            "stimuli": [{"text": "delta"}],
                        },
                    ]
                },
            ],
        },
    )
    raw_spec = IatSpec.from_yaml_file(spec_path)

    # When: the spec resolves its image paths against the spec directory.
    # Then: the missing file is rejected.
    with pytest.raises(ValueError, match="Stimulus file does not exist"):
        raw_spec.resolve(spec_path.parent)


def test_iat_spec_rejects_duplicate_category_slugs(tmp_path: Path) -> None:
    # Given: one spec file that reuses one category slug across the two category pairs.
    spec_path = tmp_path / "duplicate-category.yaml"
    write_json(
        spec_path,
        {
            "slug": "invalid-spec",
            "title": "Invalid Spec",
            "description": "Reject duplicate category slugs.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "repeated",
                            "label": "First",
                            "stimuli": [{"text": "alpha"}],
                        },
                        {
                            "slug": "other",
                            "label": "Second",
                            "stimuli": [{"text": "beta"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "repeated",
                            "label": "Third",
                            "stimuli": [{"text": "gamma"}],
                        },
                        {
                            "slug": "final",
                            "label": "Fourth",
                            "stimuli": [{"text": "delta"}],
                        },
                    ]
                },
            ],
        },
    )

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the duplicate category slug.
    with pytest.raises(ValidationError, match="Category slugs must be unique within one IAT spec"):
        IatSpec.from_yaml_file(spec_path)


def test_iat_spec_rejects_blank_category_label(tmp_path: Path) -> None:
    # Given: one spec file with one category label that contains only whitespace.
    spec_path = tmp_path / "blank-category-label.yaml"
    write_json(
        spec_path,
        {
            "slug": "age-attitudes",
            "title": "Age Attitudes IAT",
            "description": "Measures associations about age.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "young",
                            "label": "Young",
                            "stimuli": [{"text": "youth"}],
                        },
                        {
                            "slug": "old",
                            "label": "   ",
                            "stimuli": [{"text": "elder"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "pleasant",
                            "label": "Pleasant",
                            "stimuli": [{"text": "joy"}],
                        },
                        {
                            "slug": "unpleasant",
                            "label": "Unpleasant",
                            "stimuli": [{"text": "pain"}],
                        },
                    ]
                },
            ],
        },
    )

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the blank category label.
    with pytest.raises(ValidationError, match="at least 1 character"):
        IatSpec.from_yaml_file(spec_path)


def test_iat_spec_rejects_empty_category_stimuli_list(tmp_path: Path) -> None:
    # Given: one spec file with one category that defines no stimuli.
    spec_path = tmp_path / "empty-category-stimuli.yaml"
    write_json(
        spec_path,
        {
            "slug": "age-attitudes",
            "title": "Age Attitudes IAT",
            "description": "Measures associations about age.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "young",
                            "label": "Young",
                            "stimuli": [],
                        },
                        {
                            "slug": "old",
                            "label": "Old",
                            "stimuli": [{"text": "elder"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "pleasant",
                            "label": "Pleasant",
                            "stimuli": [{"text": "joy"}],
                        },
                        {
                            "slug": "unpleasant",
                            "label": "Unpleasant",
                            "stimuli": [{"text": "pain"}],
                        },
                    ]
                },
            ],
        },
    )

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the empty category stimuli list.
    with pytest.raises(ValidationError, match="at least 1 item"):
        IatSpec.from_yaml_file(spec_path)
