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

[`apps/stimuli_generator`](apps/stimuli_generator/README.md) generates synthetic image stimuli from YAML specs.

- Purpose: generate published stimulus sets from checked-in YAML specs
- Inputs: [`resources/stimuli_generation/`](resources/stimuli_generation/README.md)
- Outputs: [`resources/stimuli/`](resources/stimuli/README.md)
- Run one set: `bazel run //apps/stimuli_generator:main -- generate <spec> --output-dir <dir>`
- Run the checked-in batch: `bazel run //apps/stimuli_generator:main -- batch resources/stimuli_generation/all.yaml`

## Frontend

The participant-facing single-page frontend lives in [`apps/frontend`](apps/frontend/README.md).

- Purpose: render the participant flow for browsing IATs and completing sessions
- Build output: `//apps/frontend:dist`
- Served by: [`apps/backend`](apps/backend/README.md)
- Develop it with: `bazel run //apps/backend:main`
- Workflow: rerun the backend command after frontend changes so Bazel rebuilds the bundle and the backend serves refreshed runfiles

## Backend

The participant-facing backend lives in [`apps/backend`](apps/backend/README.md).

- Purpose: serve the frontend, published IAT definitions, public stimulus images, and the participant session API
- Inputs: [`resources/iats/`](resources/iats/README.md) and [`resources/stimuli/`](resources/stimuli/README.md)
- Run it with: `bazel run //apps/backend:main`
- Run it with explicit configuration: `IAT_RESOURCES_CONFIG_PATH=resources/backend.yaml bazel run //apps/backend:main`

## Evaluation

Runtime benchmark tooling lives in [`apps/evaluation`](apps/evaluation/README.md).

- Purpose: run Selenium Grid benchmarks against the participant app
- Inputs: [`resources/evaluation/`](resources/evaluation/README.md)
- Outputs: [`resources/evaluation-results/`](resources/evaluation-results/README.md)
- Run one spec: `bazel run //apps/evaluation:main -- spec <spec> --output-dir <dir> --app-url <url>`
- Run the checked-in batch: `bazel run //apps/evaluation:main -- batch resources/evaluation/all.yaml --app-url <url>`

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
