# Apps

Application code for this repository.

## Directories

- [`api`](api): Generated TypeScript types for backend OpenAPI schemas
- [`backend`](backend): FastAPI backend for the published IAT catalog, stimuli, and participant session flow
- [`stimuli_generator`](stimuli_generator): CLI and pipeline code for generating synthetic image stimuli from YAML specs under `resources/stimuli_generation/`

## Running app code

Use Bazel to run app binaries directly.

```bash
bazel run //apps/backend:main
bazel run //apps/stimuli_generator:main -- --help
```
