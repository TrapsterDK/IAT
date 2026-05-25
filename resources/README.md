# Resources

Generation inputs, generated assets, IAT definitions, checked-in evaluation benchmark specs, and generated evaluation output.

## Directories

- [`stimuli_generation`](stimuli_generation/README.md): Source specifications for generating synthetic stimuli sets
- [`stimuli`](stimuli/README.md): Generated stimuli assets and their manifests
- [`iats`](iats/README.md): Published IAT definitions that assemble categories and stimuli
- [`evaluation`](evaluation/README.md): Benchmark specifications and batch inputs for Selenium Grid evaluation runs
- [`evaluation-results`](evaluation-results/README.md): Generated manifests and per-worker JSON results from evaluation runs

Together these directories define what to generate, store the generated outputs, describe the tests presented by the backend, define the benchmark inputs used in runtime benchmarks, and keep generated benchmark output separate from checked-in specs.
