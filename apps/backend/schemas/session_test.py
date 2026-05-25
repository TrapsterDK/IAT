"""Tests for backend session API schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.backend.schemas.session import CompletedBlockRequest, CreateSessionRequest, SessionStimulusResponse


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"text": "alpha", "image_url": None}, id="text_only"),
        pytest.param({"text": None, "image_url": "/stimuli/example.png"}, id="image_only"),
    ],
)
def test_session_stimulus_response_accepts_exactly_one_public_representation(
    payload: dict[str, str | None],
) -> None:
    # Given: one session stimulus payload with exactly one public representation.

    # When: the public response model is validated.
    response_model = SessionStimulusResponse.model_validate(payload)

    # Then: the response model accepts the valid stimulus shape.
    assert response_model.text == payload["text"]
    assert response_model.image_url == payload["image_url"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"text": None, "image_url": None}, id="missing_both"),
        pytest.param({"text": "alpha", "image_url": "/stimuli/example.png"}, id="present_both"),
    ],
)
def test_session_stimulus_response_rejects_invalid_representation_count(payload: dict[str, str | None]) -> None:
    # Given: one session stimulus payload with zero or two public representations.

    # When: the public response model is validated.
    # Then: validation rejects the ambiguous stimulus shape.
    with pytest.raises(ValidationError, match="exactly one of 'text' or 'image_url'"):
        SessionStimulusResponse.model_validate(payload)


def test_completed_block_request_rejects_empty_trials() -> None:
    # Given: one block-upload payload with no uploaded trials.

    # When: the request model is validated.
    # Then: request validation rejects the empty block payload.
    with pytest.raises(ValidationError, match="at least 1 item"):
        CompletedBlockRequest.model_validate({"trials": []})


def test_create_session_request_accepts_one_optional_plan_seed() -> None:
    # Given: one public evaluation session-creation payload with one explicit deterministic plan seed.
    payload = {
        "iat_slug": "sample-iat",
        "client_context": None,
        "session_mode": "evaluation",
        "plan_seed": 123,
    }

    # When: the request model is validated.
    request_model = CreateSessionRequest.model_validate(payload)

    # Then: the explicit plan seed is accepted and preserved.
    assert request_model.session_mode == "evaluation"
    assert request_model.plan_seed == 123


def test_create_session_request_rejects_negative_plan_seed() -> None:
    # Given: one evaluation session-creation payload with one negative deterministic plan seed.

    # When: the request model is validated.
    # Then: validation rejects the negative seed.
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        CreateSessionRequest.model_validate({"iat_slug": "sample-iat", "session_mode": "evaluation", "plan_seed": -1})


def test_create_session_request_rejects_plan_seed_for_participant_mode() -> None:
    # Given: one participant session payload that incorrectly includes one deterministic plan seed.

    # When: the request model is validated.
    # Then: validation rejects the unsupported participant-only payload shape.
    with pytest.raises(ValidationError, match="Participant sessions must not define one 'plan_seed'"):
        CreateSessionRequest.model_validate({"iat_slug": "sample-iat", "plan_seed": 123})


def test_create_session_request_defaults_session_mode_to_participant() -> None:
    # Given: one session payload that omits the explicit session mode.

    # When: the request model is validated.
    request_model = CreateSessionRequest.model_validate({"iat_slug": "sample-iat"})

    # Then: the request falls back to participant mode.
    assert request_model.session_mode == "participant"
