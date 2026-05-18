"""Tests for backend catalog API schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.backend.schemas.catalog import StimulusResponse


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"text": "alpha", "image_url": None}, id="text_only"),
        pytest.param({"text": None, "image_url": "/api/stimuli/example.png"}, id="image_only"),
    ],
)
def test_stimulus_response_accepts_exactly_one_public_representation(payload: dict[str, str | None]) -> None:
    # Given: one public stimulus payload with exactly one representation.

    # When: the IAT response model is validated.
    response_model = StimulusResponse.model_validate(payload)

    # Then: the response model accepts the valid payload.
    assert response_model.text == payload["text"]
    assert response_model.image_url == payload["image_url"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"text": None, "image_url": None}, id="missing_both"),
        pytest.param({"text": "alpha", "image_url": "/api/stimuli/example.png"}, id="present_both"),
    ],
)
def test_stimulus_response_rejects_invalid_representation_count(payload: dict[str, str | None]) -> None:
    # Given: one public stimulus payload with zero or two representations.

    # When: the IAT response model is validated.
    # Then: validation rejects the ambiguous stimulus shape.
    with pytest.raises(ValidationError, match="exactly one of 'text' or 'image_url'"):
        StimulusResponse.model_validate(payload)
