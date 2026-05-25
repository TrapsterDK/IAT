# Evaluation resources

Checked-in benchmark specifications and batch inputs for Selenium Grid evaluation runs.

## Files

- `base.yaml`: shared defaults for benchmark specs in this directory
- `*/base.yaml`: optional nested defaults for one subgroup of specs that inherit settings from a closer base file
- `*.yaml`: runnable benchmark specs
- `all.yaml`: batch file that runs the checked-in benchmark set

The checked-in batch writes output to sibling directories under `../evaluation-results/` by default so generated manifests and raw worker output stay separate from the spec files.

Runner implementation details live in [`apps/evaluation`](../../apps/evaluation/README.md).
