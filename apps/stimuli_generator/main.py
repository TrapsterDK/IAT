"""Executable entrypoint for the stimuli generator CLI."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Literal

import typer
from diffusers.utils import logging as diffusers_logging
from huggingface_hub import utils
from transformers.utils import logging as transformers_logging

from apps.stimuli_generator.specs import (
    StimulusGenerationBatchSpec,
    StimulusGenerationSpec,
)
from apps.stimuli_generator.stable_diffusion_3_5 import (
    generate_images_with_pipeline,
    load_pipeline,
)
from libs.bazel.workspace import get_build_working_directory
from libs.path.path import resolve_path

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def _run_generation(
    resolved_pairs: list[tuple[StimulusGenerationSpec, Path]],
    device: Literal["auto", "cpu", "cuda"],
    show_progress: bool,
) -> None:
    """Run image generation for one or more resolved requests.

    Args:
        resolved_pairs: Resolved spec/output pairs.
        device: Execution device selection.
        show_progress: Whether to show Hugging Face progress bars.
    """
    if not show_progress:
        diffusers_logging.disable_progress_bar()
        transformers_logging.disable_progress_bar()
        utils.disable_progress_bars()
    else:
        diffusers_logging.enable_progress_bar()
        transformers_logging.enable_progress_bar()
        utils.enable_progress_bars()

    grouped_pairs = defaultdict(list)
    for spec, resolved_output_root in resolved_pairs:
        grouped_pairs[
            (
                spec.stimuli_generation.model.id,
                spec.stimuli_generation.model.revision,
                spec.stimuli_generation.sampling.dtype,
            )
        ].append((spec, resolved_output_root))

    for grouped_specs in grouped_pairs.values():
        pipeline = load_pipeline(grouped_specs[0][0], device)
        pipeline.set_progress_bar_config(disable=not show_progress)

        for spec, resolved_output_root in grouped_specs:
            image_directory = resolved_output_root / "images"
            image_directory.mkdir(parents=True, exist_ok=True)

            for seed, image in enumerate(
                generate_images_with_pipeline(pipeline, spec),
                start=spec.stimuli_generation.seed_start,
            ):
                image.save(image_directory / f"seed-{seed}.png", format="PNG")

            manifest_path = resolved_output_root / "manifest.yaml"
            spec.to_yaml_file(manifest_path)
            typer.echo(f"Manifest written to {manifest_path}")


@app.command("generate", help="Generate images for one spec.")
def generate_command(
    spec_path: Annotated[Path, typer.Argument(help="Leaf generation spec file.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Output directory for this spec.")],
    device: Annotated[Literal["auto", "cpu", "cuda"], typer.Option("--device")] = "auto",
    show_progress: Annotated[bool, typer.Option("--show-progress/--no-progress")] = False,
) -> None:
    """Generate images and a manifest for one generation spec.

    Args:
        spec_path: Leaf generation spec file.
        output_dir: Output directory for this spec.
        device: Execution device selection.
        show_progress: Whether to show Hugging Face progress bars.
    """
    working_directory = get_build_working_directory(os.environ) or Path.cwd()
    resolved_spec_path = resolve_path(spec_path.expanduser(), working_directory)
    _run_generation(
        [
            (
                StimulusGenerationSpec.from_file(resolved_spec_path),
                resolve_path(output_dir.expanduser(), working_directory),
            )
        ],
        device,
        show_progress,
    )


@app.command("batch", help="Generate images from an explicit batch file.")
def batch_command(
    batch_path: Annotated[Path, typer.Argument(help="Batch file with explicit spec and output_dir jobs.")],
    device: Annotated[Literal["auto", "cpu", "cuda"], typer.Option("--device")] = "auto",
    show_progress: Annotated[bool, typer.Option("--show-progress/--no-progress")] = False,
) -> None:
    """Generate images from one batch file with explicit output directories.

    Args:
        batch_path: Batch file with explicit spec and output_dir jobs.
        device: Execution device selection.
        show_progress: Whether to show Hugging Face progress bars.
    """
    working_directory = get_build_working_directory(os.environ) or Path.cwd()
    resolved_batch_path = resolve_path(batch_path.expanduser(), working_directory)
    batch = StimulusGenerationBatchSpec.from_file(resolved_batch_path).resolve(resolved_batch_path.parent)
    _run_generation(
        [
            (
                StimulusGenerationSpec.from_file(job.spec),
                job.output_dir,
            )
            for job in batch.jobs
        ],
        device,
        show_progress,
    )


if __name__ == "__main__":
    app()
