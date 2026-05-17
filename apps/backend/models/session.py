"""Public API models for session bootstrap and block uploads."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.backend.domain.session.models import ResponseSide, TrialEventType  # noqa: TC001
from libs.pydantic.types import NonBlankString, NonBlankString255

type BlockLabels = tuple[NonBlankString255] | tuple[NonBlankString255, NonBlankString255]


class ClientContextRequest(BaseModel):
    """Optional client metadata accepted when starting one session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_agent: NonBlankString | None = None
    platform: NonBlankString255 | None = None
    viewport_width_px: int | None = Field(default=None, gt=0)
    viewport_height_px: int | None = Field(default=None, gt=0)
    device_pixel_ratio: float | None = Field(default=None, gt=0)


class CreateSessionRequest(BaseModel):
    """Public request payload for creating and starting one IAT session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    iat_slug: NonBlankString255
    client_context: ClientContextRequest | None = None


class SessionStimulusResponse(BaseModel):
    """One public text or image stimulus returned in one run plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: NonBlankString255 | None = None
    image_url: NonBlankString255 | None = None

    @model_validator(mode="after")
    def validate_stimulus(self) -> Self:
        """Require exactly one public stimulus representation.

        Returns:
            The validated session stimulus response.
        """
        if (self.text is None) == (self.image_url is None):
            raise ValueError("Each session stimulus must define exactly one of 'text' or 'image_url'.")

        return self


class RunPlanTrialResponse(BaseModel):
    """One deterministic trial returned to the client runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stimulus: SessionStimulusResponse
    correct_response_side: ResponseSide


class RunPlanBlockResponse(BaseModel):
    """One deterministic block returned to the client runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left_labels: BlockLabels
    right_labels: BlockLabels
    is_practice: bool
    trials: tuple[RunPlanTrialResponse, ...] = Field(min_length=1)


class SessionBootstrapResponse(BaseModel):
    """Public session bootstrap returned when one session is created."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_key: NonBlankString255
    anticipation_threshold_ms: int = Field(ge=0)
    response_timeout_ms: int = Field(gt=0)
    blocks: tuple[RunPlanBlockResponse, ...] = Field(min_length=1)


class UploadTrialEventRequest(BaseModel):
    """One raw participant action captured while one trial was active."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: TrialEventType
    elapsed_ms: int = Field(ge=0)


class UploadBlockTrialRequest(BaseModel):
    """One completed trial uploaded within one deterministic block prefix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    events: tuple[UploadTrialEventRequest, ...] = Field(min_length=1)


class UploadBlockRequest(BaseModel):
    """One deterministic block uploaded from the client runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trials: tuple[UploadBlockTrialRequest, ...] = Field(min_length=1)
