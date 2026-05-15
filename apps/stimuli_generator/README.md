# Stimuli generator

`apps/stimuli_generator` generates synthetic image stimuli from YAML specs.

## Usage

Generate one stimulus set:

```bash
bazel run //apps/stimuli_generator:main -- generate \
  resources/stimuli_generation/face/female-asian.yaml \
  --output-dir resources/stimuli/face/female-asian
```

Generate the full batch:

```bash
bazel run //apps/stimuli_generator:main -- batch \
  resources/stimuli_generation/all.yaml
```

Useful options:

- `--device auto|cpu|cuda`: `auto` uses CUDA when available and falls back to CPU
- `--show-progress`: enables Hugging Face and diffusers progress output
