"""Executable entrypoint for the stimuli generator CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Literal

import typer

from apps.stimuli_generator.stable_diffusion_3_5 import generate_images
from apps.stimuli_generator.specs import StimulusGenerationSpec
from libs.bazel.workspace import get_build_working_directory


def generate(
    spec_path: Annotated[Path, typer.Argument()],
    output_root: Annotated[Path, typer.Argument()],
    device: Annotated[Literal["auto", "cpu", "cuda"], typer.Option("--device")] = "auto",
    show_progress: Annotated[bool, typer.Option("--show-progress/--no-progress")] = False,
) -> None:
    """Generate images and a manifest from one generation spec.

    Args:
        spec_path: Path to one leaf generation spec.
        output_root: Output directory for generated files.
        device: Execution device selection.
        show_progress: Whether to show Hugging Face progress bars.
    """
    working_directory = get_build_working_directory(os.environ) or Path.cwd()

    resolved_spec_path = spec_path.expanduser()
    if not resolved_spec_path.is_absolute():
        resolved_spec_path = working_directory / resolved_spec_path
    resolved_spec_path = resolved_spec_path.resolve()

    resolved_output_root = output_root.expanduser()
    if not resolved_output_root.is_absolute():
        resolved_output_root = working_directory / resolved_output_root
    resolved_output_root = resolved_output_root.resolve()

    spec = StimulusGenerationSpec.from_file(resolved_spec_path)
    image_directory = resolved_output_root / "images"
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    image_directory.mkdir(parents=True, exist_ok=True)

    generated_images = generate_images(
        spec,
        device,
        show_progress,
    )
    for seed, image in enumerate(generated_images, start=spec.stimuli_generation.seed_start):
        image.save(image_directory / f"{spec.slug}-seed-{seed}.png", format="PNG")

    manifest_path = resolved_output_root / "manifest.yaml"
    spec.to_yaml_file(manifest_path)
    typer.echo(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    typer.run(generate)
