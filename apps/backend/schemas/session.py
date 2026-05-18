"""Public API request and response schemas for participant session flow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.backend.models.plan import ResponseSide  # noqa: TC001
from apps.backend.models.session import (
    ClientContext,
    CompletedBlockInput,
    CompletedTrialInput,
    SessionCreateInput,
    SessionState,
    TrialEventInput,
    TrialEventType,
)
from libs.pydantic.types import NonBlankString, NonBlankString255

if TYPE_CHECKING:
    from apps.backend.models.plan import BlockPlan, PlannedStimulus, RunPlan, TrialPlan
    from apps.backend.models.scoring import SessionScoreResult

type BlockLabels = tuple[NonBlankString255] | tuple[NonBlankString255, NonBlankString255]
type StimulusUrlBuilder = Callable[[PurePosixPath], str]


class ClientContextRequest(BaseModel):
    """Optional client metadata accepted when starting one session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_agent: NonBlankString | None = None
    platform: NonBlankString255 | None = None
    viewport_width_px: int | None = Field(default=None, gt=0)
    viewport_height_px: int | None = Field(default=None, gt=0)
    device_pixel_ratio: float | None = Field(default=None, gt=0)

    def to_business(self) -> ClientContext:
        """Build one internal client-context model from the validated request.

        Returns:
            The internal client-context model.
        """
        return ClientContext(
            user_agent=self.user_agent,
            platform=self.platform,
            viewport_width_px=self.viewport_width_px,
            viewport_height_px=self.viewport_height_px,
            device_pixel_ratio=self.device_pixel_ratio,
        )


class CreateSessionRequest(BaseModel):
    """Public request payload for creating and starting one IAT session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    iat_slug: NonBlankString255
    client_context: ClientContextRequest | None = None

    def to_business(self) -> SessionCreateInput:
        """Build one internal session-creation payload from the validated request.

        Returns:
            The internal session-creation payload.
        """
        return SessionCreateInput(
            iat_slug=self.iat_slug,
            client_context=ClientContext() if self.client_context is None else self.client_context.to_business(),
        )


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

    @classmethod
    def from_business(
        cls,
        stimulus: PlannedStimulus,
        build_image_url: StimulusUrlBuilder,
    ) -> SessionStimulusResponse:
        """Build one public session stimulus from one planned stimulus.

        Args:
            stimulus: Planned stimulus to expose through the API.
            build_image_url: Builder for public image URLs.

        Returns:
            The public session stimulus response.
        """
        if stimulus.image_path is not None:
            return cls(image_url=build_image_url(stimulus.image_path))

        return cls(text=stimulus.text)


class RunPlanTrialResponse(BaseModel):
    """One deterministic trial returned to the client runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stimulus: SessionStimulusResponse
    correct_response_side: ResponseSide

    @classmethod
    def from_business(cls, trial: TrialPlan, build_image_url: StimulusUrlBuilder) -> RunPlanTrialResponse:
        """Build one public trial response from one planned trial.

        Args:
            trial: Planned trial to expose through the API.
            build_image_url: Builder for public image URLs.

        Returns:
            The public run-plan trial response.
        """
        return cls(
            stimulus=SessionStimulusResponse.from_business(trial.stimulus, build_image_url),
            correct_response_side=trial.correct_response_side,
        )


class RunPlanBlockResponse(BaseModel):
    """One deterministic block returned to the client runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left_labels: BlockLabels
    right_labels: BlockLabels
    is_practice: bool
    trials: tuple[RunPlanTrialResponse, ...] = Field(min_length=1)

    @classmethod
    def from_business(cls, block: BlockPlan, build_image_url: StimulusUrlBuilder) -> RunPlanBlockResponse:
        """Build one public block response from one planned block.

        Args:
            block: Planned block to expose through the API.
            build_image_url: Builder for public image URLs.

        Returns:
            The public run-plan block response.
        """
        return cls(
            left_labels=block.left_labels,
            right_labels=block.right_labels,
            is_practice=block.is_practice,
            trials=tuple(RunPlanTrialResponse.from_business(trial, build_image_url) for trial in block.trials),
        )


class SessionBootstrapResponse(BaseModel):
    """Public session bootstrap returned when one session is created."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_key: NonBlankString255
    blocks: tuple[RunPlanBlockResponse, ...] = Field(min_length=1)

    @classmethod
    def from_business(
        cls,
        state: SessionState,
        run_plan: RunPlan,
        build_image_url: StimulusUrlBuilder,
    ) -> SessionBootstrapResponse:
        """Build one public session bootstrap response from persisted session state.

        Args:
            state: Persisted session state.
            run_plan: Deterministic run plan assigned to the session.
            build_image_url: Builder for public image URLs.

        Returns:
            The public session bootstrap response.
        """
        return cls(
            session_key=state.session_key,
            blocks=tuple(RunPlanBlockResponse.from_business(block, build_image_url) for block in run_plan.blocks),
        )


class SessionScoreResponse(BaseModel):
    """Public response payload for one computed completed-session score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    d_score: float
    headline: NonBlankString

    @classmethod
    def from_business(cls, session_score: SessionScoreResult) -> SessionScoreResponse:
        """Build one public score response from one computed score result.

        Args:
            session_score: Computed session score result.

        Returns:
            The public score response.
        """
        return cls(d_score=session_score.d_score, headline=session_score.headline)


class TrialEventRequest(BaseModel):
    """One raw participant action captured while one trial was active."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: TrialEventType
    elapsed_ms: int = Field(ge=0)

    def to_business(self) -> TrialEventInput:
        """Build one typed internal trial-event payload from the validated request.

        Returns:
            The internal trial-event payload.
        """
        return TrialEventInput(event_type=self.event_type, elapsed_ms=self.elapsed_ms)


class CompletedTrialRequest(BaseModel):
    """One completed trial uploaded within one deterministic block prefix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    events: tuple[TrialEventRequest, ...] = Field(min_length=1)

    def to_business(self) -> CompletedTrialInput:
        """Build one typed internal trial payload from the validated request.

        Returns:
            The internal trial payload.
        """
        return CompletedTrialInput(events=tuple(event_request.to_business() for event_request in self.events))


class CompletedBlockRequest(BaseModel):
    """One deterministic block uploaded from the client runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trials: tuple[CompletedTrialRequest, ...] = Field(min_length=1)

    def to_business(self) -> CompletedBlockInput:
        """Build one typed internal block payload from the validated request.

        Returns:
            The internal block payload.
        """
        return CompletedBlockInput(trials=tuple(completed_trial.to_business() for completed_trial in self.trials))
