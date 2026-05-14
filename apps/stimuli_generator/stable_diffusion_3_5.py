"""Stable Diffusion 3.5 Medium image generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import accelerate  # noqa: F401
import torch
import torchvision  # noqa: F401
import transformers  # noqa: F401
from diffusers.pipelines.stable_diffusion_3.pipeline_stable_diffusion_3 import StableDiffusion3Pipeline

if TYPE_CHECKING:
    from PIL.Image import Image

    from apps.stimuli_generator.specs import StimulusGenerationSpec


TORCH_DTYPES: dict[Literal["bfloat16", "float16"], torch.dtype] = {
    "bfloat16": torch.bfloat16,
    "float16": torch.float16,
}


def load_pipeline(
    spec: StimulusGenerationSpec,
    device: Literal["auto", "cpu", "cuda"],
) -> StableDiffusion3Pipeline:
    """Load and place one Stable Diffusion pipeline for generation.

    Args:
        spec: One validated generation spec.
        device: Execution device selection.

    Returns:
        The configured Stable Diffusion pipeline.
    """
    pipeline = StableDiffusion3Pipeline.from_pretrained(
        spec.stimuli_generation.model.id,
        revision=spec.stimuli_generation.model.revision,
        torch_dtype=TORCH_DTYPES[spec.stimuli_generation.sampling.dtype],
    )

    cuda_available = torch.cuda.is_available()
    if device == "cuda" and not cuda_available:
        raise RuntimeError("CUDA was requested explicitly but no CUDA device is available.")

    if device == "cpu" or not cuda_available:
        pipeline.to("cpu")
    else:
        pipeline.enable_model_cpu_offload()

    return pipeline


def generate_images_with_pipeline(
    pipeline: StableDiffusion3Pipeline,
    spec: StimulusGenerationSpec,
) -> list[Image]:
    """Generate images for one spec using one loaded pipeline.

    Args:
        pipeline: One loaded Stable Diffusion pipeline.
        spec: One validated generation spec.

    Returns:
        The generated images.
    """
    output_mode = "L" if spec.stimuli_generation.image.color_mode == "grayscale" else "RGB"
    images: list[Image] = []

    for seed in range(
        spec.stimuli_generation.seed_start,
        spec.stimuli_generation.seed_start + spec.stimuli_generation.count,
    ):
        result = pipeline(
            prompt=spec.stimuli_generation.prompts.prompt,
            prompt_3=spec.stimuli_generation.prompts.prompt_3,
            negative_prompt=spec.stimuli_generation.prompts.negative_prompt,
            num_inference_steps=spec.stimuli_generation.sampling.num_inference_steps,
            height=spec.stimuli_generation.image.height,
            width=spec.stimuli_generation.image.width,
            guidance_scale=spec.stimuli_generation.sampling.guidance_scale,
            generator=torch.Generator(device="cpu").manual_seed(seed),
            max_sequence_length=spec.stimuli_generation.sampling.max_sequence_length,
            skip_guidance_layers=spec.stimuli_generation.sampling.skip_guidance_layers,
            skip_layer_guidance_scale=spec.stimuli_generation.sampling.skip_layer_guidance_scale,
            skip_layer_guidance_start=spec.stimuli_generation.sampling.skip_layer_guidance_start,
            skip_layer_guidance_stop=spec.stimuli_generation.sampling.skip_layer_guidance_stop,
        )
        images.append(result.images[0].convert(output_mode))

    return images
