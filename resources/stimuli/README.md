# Stimuli

Generated stimulus assets and their manifests.

## Layout

- `face/<stimulus-set>/manifest.yaml`: metadata for one generated stimulus set
- `face/<stimulus-set>/images/`: generated images for that set

The checked-in output layout mirrors the batch definitions under [`resources/stimuli_generation/`](../stimuli_generation/README.md).

## Usage

The backend serves these published stimulus assets, and the IAT definitions under [`resources/iats/`](../iats/README.md) reference them by path.

Each generated stimulus-set directory is an output artifact. Treat the generation specs as the source of truth and regenerate these files when prompts, seeds, or generation settings change.
