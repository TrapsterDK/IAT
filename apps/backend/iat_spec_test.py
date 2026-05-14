"""Tests for typed IAT spec loading and validation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from apps.backend.iat_spec import IatSpec

if TYPE_CHECKING:
    from pathlib import Path


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_iat_spec_loads_valid_yaml_file(tmp_path: Path) -> None:
    # Given: one valid IAT spec file written in YAML.
    spec_path = tmp_path / "valid-spec.yaml"
    _write_json(
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


def test_iat_spec_coerces_yaml_lists_to_fixed_length_tuples(tmp_path: Path) -> None:
    # Given: one spec file written with YAML lists for its category pairs and categories.
    spec_path = tmp_path / "tuple-shape.yaml"
    _write_json(
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


def test_iat_spec_rejects_duplicate_category_slugs(tmp_path: Path) -> None:
    # Given: one spec file that reuses one category slug across the two category pairs.
    spec_path = tmp_path / "duplicate-category.yaml"
    _write_json(
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
