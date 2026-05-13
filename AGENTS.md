This repository uses Bazel.

Commands:

- `tool format`: apply formatting fixes.
- `tool lint`: run linters; use fix mode when needed.
- `tool update`: refresh dependency locks and generated dependency metadata.
- `tool configure`: generate or regenerate `BUILD.bazel` files.
- Use `--bazel_flag=--config=ai` with wrapper commands to reduce noise.
- Run `<command> --help` to inspect wrapper command options.
- For targeted verification, prefer direct Bazel commands such as `bazel test --config=ai //path:target`.

Code rules:

- Run format and lint after code changes.
- Treat warnings as errors.
- Do not add `__init__.py` files unless there is a concrete non-Bazel need.
- Keep Bazel metadata up to date. Run `configure` when BUILD files need regeneration.

Test rules:

- Use `# Given: ...`, `# When: ...`, and `# Then: ...` comments on separate lines in every test, even simple ones. Always include all 3, and never use bare phase labels without a short description.
- Add brief extra comments for meaningful setup, data construction, intermediate checks, expectations, and cleanup when they improve clarity.
- Do not name variables `given`, `when`, or `then`; use descriptive names.
- Prefer parametrization for repeated cases. Keep cases with the same behavior together, including simple boundary cases such as an empty list `[]` when it follows the same assertion pattern as the non-empty cases. Do not put conditional logic inside parametrized tests.
- In parametrized tests, use `pytest.param(...)` for each case instead of bare tuples or bare values so you can name and extend cases consistently.
- Split out a separate test when behavior, setup, or assertions differ meaningfully, such as exceptions, side effects, or distinct control flow.
- Do not use mocks; test real deterministic behavior and avoid time, network, and hidden global-state dependencies.
- Avoid unnecessary assignments or helper variables that do not improve test clarity.
