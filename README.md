# IAT

## Start

With `direnv`:

```bash
direnv allow
bazel run //tools:env
```

Without `direnv`:

```bash
bazel run //tools:env
```

That command creates wrapper tools under `bazel-out/bazel_env-opt/bin/tools/bazel_env/bin` and refreshes the local `venv/`.

## Stimuli generation

This project uses synthetic image stimuli generated from YAML specs. The generation pipeline lives in [`apps/stimuli_generator`](apps/stimuli_generator/README.md), which provides the CLI for creating those assets.

## Frontend

The participant-facing frontend lives in [`apps/frontend`](apps/frontend/README.md). The backend serves its built shell and bundled assets.

## Backend

The participant-facing backend lives in [`apps/backend`](apps/backend/README.md). It serves the built frontend, published IAT definitions, public stimulus images, session creation, block uploads, and score retrieval.

## Resources

The [`resources/`](resources/README.md) tree holds generation inputs, generated assets, IAT definitions, checked-in evaluation benchmark specs, and generated evaluation output.

- [`resources/stimuli_generation/`](resources/stimuli_generation/README.md): source YAML specs and batch files for synthetic stimulus generation
- [`resources/stimuli/`](resources/stimuli/README.md): generated stimulus sets, including manifests and image assets
- [`resources/iats/`](resources/iats/README.md): IAT definitions that reference stimuli from `resources/stimuli`
- [`resources/evaluation/`](resources/evaluation/README.md): benchmark specs and batch inputs for Selenium Grid evaluation runs
- [`resources/evaluation-results/`](resources/evaluation-results/README.md): default output location for generated evaluation manifests and per-worker JSON results

Together these directories define what to generate, store the generated assets, describe the IATs that use them, define the benchmark inputs used in runtime benchmarks, and keep generated evaluation output separate from checked-in specs.

## Common commands

```bash
tool format
tool lint
tool test
tool configure
tool update
```

## Docs

- [Documentation index](docs/README.md)
- [Tooling](docs/tooling.md)
