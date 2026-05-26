# Tooling

## Bootstrap

```bash
bazel run //tools:env
```

That command creates wrapper tools under `bazel-out/bazel_env-opt/bin/tools/bazel_env/bin` and refreshes `.venv/`.

Use those commands from a reloaded `direnv` shell, through `bazel run //tools/cli:main -- <command>`, or by calling the generated wrapper path directly.

## Main commands

- `tool format`: format files
- `tool lint`: lint and static analysis; defaults to fix mode
- `tool test`: run `bazel test`
- `tool build`: run `bazel build`
- `tool configure`: refresh `BUILD.bazel` files
- `tool update`: refresh lock files and dependency metadata

Use `--bazel_flag=--config=ai` for quieter output.

## Examples

```bash
tool lint docs/README.md
tool test //tools/javascript:lock_test
tool lint --no-fix
```

`tool format` takes file paths. `tool build`, `tool test`, and `tool lint` take Bazel labels, workspace-relative paths, or both.

## When to use configure and update

- Run `tool configure` after adding, moving, or deleting source files.
- Run `tool update bazel` for `MODULE.bazel` or `MODULE.bazel.lock` changes.
- Run `tool update python` for Python dependency changes.
- Run `tool update javascript` for JavaScript dependency changes.
