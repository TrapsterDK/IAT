# Libraries

Shared Python libraries used across apps and tooling.

## Directories

- [`bazel`](bazel): Bazel workspace, command, target, artifact, and Build Event Protocol helpers
- [`configuration`](config): Typed configuration loading and inheritance helpers for YAML, JSON, and TOML files
- [`path`](path): Filesystem path resolution helpers
- [`pydantic`](pydantic): Shared Pydantic types for common validation rules
- [`database types`](sqlalchemy): Shared database column types
- [`testing`](testing): Helpers for writing test fixtures

These libraries support apps and tooling rather than acting as standalone entrypoints.

`testing` supports repository tests and stays out of production code.
