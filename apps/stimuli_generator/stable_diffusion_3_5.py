"""Stable Diffusion 3.5 Medium image generation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

import accelerate  # noqa: F401
import torch
import transformers  # noqa: F401
from diffusers import StableDiffusion3Pipeline

if TYPE_CHECKING:
    from PIL.Image import Image

    from apps.stimuli_generator.specs import StimulusGenerationSpec


def generate_images(
    spec: StimulusGenerationSpec,
    device: Literal["auto", "cpu", "cuda"],
    show_progress: bool,
) -> list[Image]:
    """Generate all images in one leaf spec.

    Args:
        spec: One validated generation spec.
        device: Execution device selection.
        show_progress: Whether to show Hugging Face progress bars.

    Returns:
        The generated images.
    """
    if not show_progress:
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    else:
        os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)

    pipeline_kwargs = {
        "torch_dtype": torch.bfloat16 if spec.stimuli_generation.sampling.dtype == "bfloat16" else torch.float16,
        "revision": spec.stimuli_generation.model.revision,
    }

    pipeline = StableDiffusion3Pipeline.from_pretrained(
        spec.stimuli_generation.model.id,
        **pipeline_kwargs,
    )
    pipeline.set_progress_bar_config(disable=not show_progress)

    cuda_available = torch.cuda.is_available()
    if device == "cuda" and not cuda_available:
        raise RuntimeError("CUDA was requested explicitly but no CUDA device is available.")

    if device == "cpu" or not cuda_available:
        pipeline.to("cpu")
    else:
        pipeline.enable_model_cpu_offload()

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
