"""Config models for synthetic stimulus generation."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from libs.config.config import ConfigModel
from libs.config.extending_config import ExtendingConfigModel


class ImageSettings(ConfigModel):
    """Output image settings."""

    width: int = Field(gt=0)
    height: int = Field(gt=0)
    color_mode: Literal["rgb", "grayscale"] = "rgb"

    @model_validator(mode="after")
    def validate_image_settings(self) -> ImageSettings:
        """Validate one image-settings block.

        Returns:
            The validated image settings.
        """
        if self.width % 8 != 0 or self.height % 8 != 0:
            raise ValueError("Image width and height must be divisible by 8.")
        return self


class PromptSettings(ConfigModel):
    """Prompt text sent to the model."""

    prompt: str
    prompt_3: str
    negative_prompt: str = ""

    @model_validator(mode="after")
    def validate_prompt_settings(self) -> PromptSettings:
        """Validate one prompts block.

        Returns:
            The validated prompt settings.
        """
        if not self.prompt:
            raise ValueError("The prompt must not be empty.")
        if not self.prompt_3:
            raise ValueError("The prompt_3 value must not be empty.")
        return self


class ModelReference(ConfigModel):
    """Model identifier and optional pinned revision."""

    id: str
    revision: str

    @model_validator(mode="after")
    def validate_model_reference(self) -> ModelReference:
        """Validate one model block.

        Returns:
            The validated model reference.
        """
        if not self.id:
            raise ValueError("Model identifiers must not be empty.")
        if not self.revision:
            raise ValueError("Model revisions must not be empty.")
        return self


class SamplingSettings(ConfigModel):
    """Sampling settings passed to the pipeline."""

    dtype: Literal["bfloat16", "float16"] = "float16"
    guidance_scale: float = Field(default=7.0, ge=0.0)
    max_sequence_length: int = Field(default=256, gt=0)
    num_inference_steps: int = Field(default=28, gt=0)
    skip_guidance_layers: list[int] = Field(default_factory=list)
    skip_layer_guidance_scale: float = Field(default=0.0, ge=0.0)
    skip_layer_guidance_start: float = Field(default=0.0, ge=0.0, le=1.0)
    skip_layer_guidance_stop: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_sampling_settings(self) -> SamplingSettings:
        """Validate one sampling block.

        Returns:
            The validated sampling settings.
        """
        if self.skip_layer_guidance_stop < self.skip_layer_guidance_start:
            raise ValueError("Skip-layer guidance stop must be greater than or equal to the start.")
        return self


class StimuliGenerationSettings(ConfigModel):
    """All generation settings for one stimulus set."""

    count: int = Field(gt=0)
    seed_start: int = Field(ge=0)
    image: ImageSettings
    prompts: PromptSettings
    model: ModelReference
    sampling: SamplingSettings = Field(default_factory=SamplingSettings)


class StimulusGenerationSpec(ExtendingConfigModel):
    """One runnable leaf spec for synthetic stimulus generation."""

    slug: str
    description: str
    stimuli_generation: StimuliGenerationSettings

    @model_validator(mode="after")
    def validate_spec(self) -> StimulusGenerationSpec:
        """Validate one fully resolved leaf spec.

        Returns:
            The validated spec instance.
        """
        if not self.slug:
            raise ValueError("Spec slugs must not be empty.")
        if not self.description:
            raise ValueError("Spec descriptions must not be empty.")
        return self
