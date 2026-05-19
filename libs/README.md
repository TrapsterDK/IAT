# Libraries

Shared Python libraries used across apps and tooling.

## Directories

- [`bazel`](bazel): Bazel workspace, command, target, artifact, and Build Event Protocol helpers
- [`config`](config): Typed config loading and inheritance helpers for YAML, JSON, and TOML files
- [`path`](path): Filesystem path resolution helpers
- [`pydantic`](pydantic): Shared Pydantic type aliases and validators
- [`sqlalchemy`](sqlalchemy): Shared SQLAlchemy column types
- [`testing`](testing): Test-only fixture writing helpers

These libraries are internal shared building blocks rather than standalone entrypoints.

`testing` is test-only and is intended for repository tests.
