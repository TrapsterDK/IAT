"""Tests for stimuli generation spec loading and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pydantic import ValidationError

from apps.stimuli_generator.specs import StimulusGenerationBatchSpec, StimulusGenerationSpec

if TYPE_CHECKING:
    from pathlib import Path


def _write_yaml(path: Path, payload: object) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _valid_spec_payload() -> dict[str, Any]:
    return {
        "slug": "white",
        "description": "Synthetic White adult face stimuli.",
        "stimuli_generation": {
            "count": 2,
            "seed_start": 4,
            "image": {
                "width": 512,
                "height": 512,
                "color_mode": "grayscale",
            },
            "prompts": {
                "prompt": "semi-realistic studio portrait of one person",
                "prompt_3": "A controlled studio portrait of one person.",
                "negative_prompt": "text, watermark",
            },
            "model": {
                "id": "stabilityai/stable-diffusion-3.5-medium",
                "revision": "b940f670f0eda2d07fbb75229e779da1ad11eb80",
            },
        },
    }


def test_stimulus_generation_spec_loads_valid_yaml_file(tmp_path: Path) -> None:
    # Given: one valid generation spec file written in YAML.
    spec_path = tmp_path / "valid-spec.yaml"
    _write_yaml(spec_path, _valid_spec_payload())

    # When: the spec is loaded through the typed model.
    resolved_spec = StimulusGenerationSpec.from_file(spec_path)

    # Then: the YAML file validates and fills the default sampling settings.
    assert resolved_spec.slug == "white"
    assert resolved_spec.stimuli_generation.sampling.dtype == "float16"
    assert resolved_spec.stimuli_generation.sampling.num_inference_steps == 28


def test_stimulus_generation_spec_merges_extended_yaml_files(tmp_path: Path) -> None:
    # Given: one base YAML spec file and one child YAML spec file that overrides nested fields.
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "white.yaml"
    _write_yaml(
        base_path,
        {
            "stimuli_generation": {
                "count": 12,
                "seed_start": 8,
                "image": {
                    "width": 1024,
                    "height": 1024,
                },
                "prompts": {
                    "negative_prompt": "text, watermark",
                },
                "model": {
                    "id": "stabilityai/stable-diffusion-3.5-medium",
                    "revision": "b940f670f0eda2d07fbb75229e779da1ad11eb80",
                },
            }
        },
    )
    _write_yaml(
        child_path,
        {
            "extends": "./base.yaml",
            "slug": "white",
            "description": "Synthetic White adult face stimuli.",
            "stimuli_generation": {
                "image": {
                    "color_mode": "grayscale",
                },
                "prompts": {
                    "prompt": "semi-realistic studio portrait of one person",
                    "prompt_3": "A controlled studio portrait of one person.",
                },
            },
        },
    )

    # When: the child spec is loaded through the typed model.
    resolved_spec = StimulusGenerationSpec.from_file(child_path)

    # Then: inheritance merges the nested image and prompt settings into one runnable spec.
    assert resolved_spec.stimuli_generation.count == 12
    assert resolved_spec.stimuli_generation.image.width == 1024
    assert resolved_spec.stimuli_generation.image.color_mode == "grayscale"
    assert resolved_spec.stimuli_generation.prompts.negative_prompt == "text, watermark"


def test_stimulus_generation_spec_rejects_image_width_not_divisible_by_8(tmp_path: Path) -> None:
    # Given: one generation spec file with one image width that is not divisible by 8.
    spec_path = tmp_path / "invalid-image-width.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["stimuli_generation"]["image"]["width"] = 510
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the invalid image dimensions.
    with pytest.raises(ValidationError, match=r"multiple of 8"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_image_height_not_divisible_by_8(tmp_path: Path) -> None:
    # Given: one generation spec file with one image height that is not divisible by 8.
    spec_path = tmp_path / "invalid-image-height.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["stimuli_generation"]["image"]["height"] = 510
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the invalid image dimensions.
    with pytest.raises(ValidationError, match=r"multiple of 8"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_empty_prompt(tmp_path: Path) -> None:
    # Given: one generation spec file with one blank prompt value.
    spec_path = tmp_path / "invalid-prompt.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["stimuli_generation"]["prompts"]["prompt"] = ""
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the blank prompt.
    with pytest.raises(ValidationError, match=r"at least 1 character"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_empty_prompt_3(tmp_path: Path) -> None:
    # Given: one generation spec file with one blank prompt_3 value.
    spec_path = tmp_path / "invalid-prompt-3.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["stimuli_generation"]["prompts"]["prompt_3"] = ""
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the blank prompt_3 value.
    with pytest.raises(ValidationError, match=r"at least 1 character"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_empty_model_identifier(tmp_path: Path) -> None:
    # Given: one generation spec file with one blank model identifier.
    spec_path = tmp_path / "invalid-model.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["stimuli_generation"]["model"]["id"] = ""
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the blank model identifier.
    with pytest.raises(ValidationError, match=r"at least 1 character"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_empty_model_revision(tmp_path: Path) -> None:
    # Given: one generation spec file with one blank model revision.
    spec_path = tmp_path / "invalid-model-revision.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["stimuli_generation"]["model"]["revision"] = ""
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the blank model revision.
    with pytest.raises(ValidationError, match=r"at least 1 character"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_skip_layer_guidance_stop_before_start(tmp_path: Path) -> None:
    # Given: one generation spec file with one skip-layer guidance stop before its start.
    spec_path = tmp_path / "invalid-sampling.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["stimuli_generation"]["sampling"] = {
        "skip_layer_guidance_start": 0.4,
        "skip_layer_guidance_stop": 0.2,
    }
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the invalid skip-layer guidance range.
    with pytest.raises(
        ValidationError,
        match=r"Skip-layer guidance stop must be greater than or equal to the start\.",
    ):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_empty_slug(tmp_path: Path) -> None:
    # Given: one generation spec file with one blank slug.
    spec_path = tmp_path / "invalid-slug.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["slug"] = ""
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the blank spec slug.
    with pytest.raises(ValidationError, match=r"at least 1 character"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_spec_rejects_empty_description(tmp_path: Path) -> None:
    # Given: one generation spec file with one blank description.
    spec_path = tmp_path / "invalid-description.yaml"
    invalid_payload = _valid_spec_payload()
    invalid_payload["description"] = ""
    _write_yaml(spec_path, invalid_payload)

    # When: the invalid spec is loaded through the typed model.
    # Then: validation rejects the blank spec description.
    with pytest.raises(ValidationError, match=r"at least 1 character"):
        StimulusGenerationSpec.from_file(spec_path)


def test_stimulus_generation_batch_spec_rejects_duplicate_output_directories(tmp_path: Path) -> None:
    # Given: one batch file with two jobs that use the same output directory.
    batch_path = tmp_path / "duplicate-output-dir.yaml"
    _write_yaml(
        batch_path,
        {
            "jobs": [
                {
                    "spec": "./specs/white.yaml",
                    "output_dir": "./out/shared",
                },
                {
                    "spec": "./specs/black.yaml",
                    "output_dir": "./out/shared",
                },
            ]
        },
    )

    # When: the invalid batch file is loaded through the typed model.
    # Then: validation rejects duplicate output directories.
    with pytest.raises(ValidationError, match=r"Each generated spec must use its own output directory\."):
        StimulusGenerationBatchSpec.from_file(batch_path)
