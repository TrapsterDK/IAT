"""Pydantic API schemas for requests and responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base API model with alias-aware validation and serialization."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class TestListItem(ApiModel):
    """A lightweight test summary for the landing page."""

    id: int
    slug: str
    title: str
    description: str


class TestListResponse(ApiModel):
    """List of tests exposed to the frontend."""

    tests: list[TestListItem]


class CategorySummary(ApiModel):
    """A serialized category definition."""

    id: int
    code: str
    label: str


class StimulusSummary(ApiModel):
    """A serialized stimulus usable by the frontend runner."""

    id: int
    content_type: Literal["text", "image"] = Field(alias="contentType")
    text_value: str | None = Field(alias="textValue")
    asset_path: str | None = Field(alias="assetPath")


class PhaseCategorySummary(ApiModel):
    """A phase-local category label."""

    id: int
    label: str


class PhaseSideCategories(ApiModel):
    """The left/right category mapping for a phase."""

    left: list[PhaseCategorySummary]
    right: list[PhaseCategorySummary]


class PhaseSummary(ApiModel):
    """A serialized phase definition."""

    id: int
    sequence_number: int = Field(alias="sequenceNumber")
    showings_per_category: int = Field(alias="showingsPerCategory")
    categories: PhaseSideCategories


class AttemptSummaryPayload(ApiModel):
    """Serialized attempt identifiers for a frontend run."""

    public_id: str = Field(alias="publicId")
    seed: int
    attempt_token: str = Field(alias="attemptToken")


class TestSummaryPayload(ApiModel):
    """Serialized test metadata for a frontend attempt."""

    slug: str
    title: str
    description: str


class VariantSummaryPayload(ApiModel):
    """Serialized variant metadata for a frontend attempt."""

    key_event_mode: Literal["keydown", "keyup"] = Field(alias="keyEventMode")
    keyboard_shortcuts: dict[Literal["left", "right"], str] = Field(alias="keyboardShortcuts")
    preload_assets: bool = Field(alias="preloadAssets")
    inter_trial_interval_ms: int = Field(alias="interTrialIntervalMs")
    response_timeout_ms: int = Field(alias="responseTimeoutMs")


class TestPayload(ApiModel):
    """Full payload needed to execute an attempt in the frontend."""

    attempt: AttemptSummaryPayload
    test: TestSummaryPayload
    variant: VariantSummaryPayload
    categories: list[CategorySummary]
    stimuli_by_category: dict[str, list[StimulusSummary]] = Field(alias="stimuliByCategory")
    phases: list[PhaseSummary]


class EnvironmentPayload(ApiModel):
    """Client environment metrics collected during an attempt."""

    user_agent: str = Field(alias="userAgent")
    platform: str = Field(max_length=120)
    language: str = Field(max_length=20)
    viewport_width: int = Field(alias="viewportWidth", gt=0)
    viewport_height: int = Field(alias="viewportHeight", gt=0)
    device_pixel_ratio: float = Field(alias="devicePixelRatio", gt=0)
    visibility_interruptions: int = Field(alias="visibilityInterruptions", ge=0)


class ShowingInputPayload(ApiModel):
    """One submitted click or keypress within a showing."""

    input_index: int = Field(alias="inputIndex", ge=0)
    side: Literal["left", "right"]
    input_source: Literal["keyboard", "button"] = Field(alias="inputSource")
    event_timestamp_ms: float = Field(alias="eventTimestampMs", ge=0)
    handler_timestamp_ms: float = Field(alias="handlerTimestampMs", ge=0)


class ShowingPayload(ApiModel):
    """One submitted showing with all input-level details."""

    phase_id: int = Field(alias="phaseId")
    stimulus_id: int = Field(alias="stimulusId")
    showing_index: int = Field(alias="showingIndex")
    stimulus_onset_ms: float = Field(alias="stimulusOnsetMs", ge=0)
    inputs: list[ShowingInputPayload]


class AttemptCompletionRequest(ApiModel):
    """Attempt completion payload sent by the frontend."""

    attempt_token: str = Field(alias="attemptToken", min_length=1)
    environment: EnvironmentPayload
    showings: list[ShowingPayload]


class CompletionSummary(ApiModel):
    """Aggregate summary metrics returned after completion."""

    showing_count: int = Field(alias="showingCount")
    accuracy: float
    mean_initial_reaction_time_ms: float = Field(alias="meanInitialReactionTimeMs")
    mean_completed_reaction_time_ms: float = Field(alias="meanCompletedReactionTimeMs")
    d_score: float = Field(alias="dscore")


class AttemptCompletionResponse(ApiModel):
    """Completion response returned to the frontend."""

    attempt_id: str = Field(alias="attemptId")
    variant: str
    summary: CompletionSummary


class ApiErrorResponse(ApiModel):
    """Error response payload for API endpoints."""

    error: str
