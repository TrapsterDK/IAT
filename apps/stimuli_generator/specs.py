"""Config models for synthetic stimulus generation."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Literal, Self

from pydantic import Field, model_validator

from libs.config.config import ConfigModel
from libs.config.extending_config import ExtendingConfigModel
from libs.path.path import resolve_path
from libs.pydantic.types import AbsoluteFilePath, AbsolutePath, NonBlankString  # noqa: TC001


class ImageSettings(ConfigModel):
    """Output image settings."""

    width: int = Field(gt=0, multiple_of=8)
    height: int = Field(gt=0, multiple_of=8)
    color_mode: Literal["rgb", "grayscale"] = "rgb"


class PromptSettings(ConfigModel):
    """Prompt text sent to the model."""

    prompt: NonBlankString
    prompt_3: NonBlankString
    negative_prompt: str = ""


class ModelReference(ConfigModel):
    """Model identifier and optional pinned revision."""

    id: NonBlankString
    revision: NonBlankString


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

    slug: NonBlankString
    description: NonBlankString
    stimuli_generation: StimuliGenerationSettings


class StimulusGenerationBatchJob(ConfigModel):
    """One explicit generation job in a batch file."""

    spec: Path
    output_dir: Path

    def resolve(self, base_directory: Path) -> ResolvedStimulusGenerationBatchJob:
        """Resolve one batch job against one batch-file directory.

        Args:
            base_directory: Directory used for relative path resolution.

        Returns:
            The resolved batch job.
        """
        return ResolvedStimulusGenerationBatchJob(
            spec=resolve_path(self.spec, base_directory),
            output_dir=resolve_path(self.output_dir, base_directory),
        )


class StimulusGenerationBatchSpec(ConfigModel):
    """Explicit batch input for multiple generation jobs."""

    jobs: list[StimulusGenerationBatchJob] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_output_directories(self) -> Self:
        """Reject duplicate output directories within one batch.

        Returns:
            The validated batch spec.
        """
        output_dirs = [job.output_dir for job in self.jobs]
        if len(output_dirs) != len(set(output_dirs)):
            raise ValueError("Each generated spec must use its own output directory.")

        return self

    def resolve(self, base_directory: Path) -> ResolvedStimulusGenerationBatchSpec:
        """Resolve one batch spec against one batch-file directory.

        Args:
            base_directory: Directory used for relative path resolution.

        Returns:
            The resolved batch spec.
        """
        return ResolvedStimulusGenerationBatchSpec(
            jobs=[job.resolve(base_directory) for job in self.jobs],
        )


class ResolvedStimulusGenerationBatchJob(StimulusGenerationBatchJob):
    """One batch job whose paths have been resolved to absolute paths."""

    spec: AbsoluteFilePath
    output_dir: AbsolutePath


class ResolvedStimulusGenerationBatchSpec(StimulusGenerationBatchSpec):
    """One batch spec whose jobs have been resolved to absolute paths."""

    jobs: list[ResolvedStimulusGenerationBatchJob] = Field(min_length=1)
