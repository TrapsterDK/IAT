# IAT

This repository keeps the Bazel tooling scaffold and one runnable target: the Project Implicit asset download command.

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
