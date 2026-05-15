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

Use those commands from a reloaded `direnv` shell, through `bazel run //tools/cli:main -- <command>`, or by calling the generated wrapper path directly.

## Stimuli generation

This project uses synthetic image stimuli generated from YAML specs. The generation pipeline lives in [`apps/stimuli_generator`](apps/stimuli_generator/README.md), which provides the CLI for creating those assets.

## Resources

The `resources/` tree holds generation inputs, generated assets, and IAT definitions.

- `resources/stimuli_generation`: source YAML specs and batch files for synthetic stimulus generation
- `resources/stimuli`: generated stimulus sets, including manifests and image assets
- `resources/iats`: IAT definitions that reference stimuli from `resources/stimuli`

Together these directories define what to generate, store the generated assets, and describe the IATs that use them.

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
