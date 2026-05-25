# Stimuli generation

Checked-in specifications and batch inputs for synthetic stimulus generation.

## Files

- `base.yaml`: shared defaults for stimulus generation runs such as image size, seed range, and model settings
- `*/base.yaml`: optional nested defaults for one subgroup of specs that inherit settings from a closer base file
- `all.yaml`: batch file that runs the checked-in stimulus generation set
- `face/*.yaml`: runnable stimulus generation specs for individual published stimulus sets

The checked-in batch writes generated output to sibling directories under [`../stimuli/`](../stimuli/README.md) so specs and generated assets stay separate.
