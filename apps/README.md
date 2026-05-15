# Apps

The `apps/` tree holds app code for this repository.

## Directories

- [`stimuli_generator`](stimuli_generator): CLI and pipeline code for generating synthetic image stimuli from YAML specs under `resources/stimuli_generation/`

## Running app code

Use Bazel to run app binaries directly.

```bash
bazel run //apps/stimuli_generator:main -- --help
```
