# Evaluation results

Generated manifests, per-worker result files, and the matching SQLite database from Selenium Grid evaluation runs.

## Layout

- `<condition>/manifest.yaml`: evaluation manifest for one benchmark condition
- `<condition>/<worker>.yaml`: result file written by one Selenium Grid worker
- `backend.sqlite3`: SQLite database containing persisted sessions for the checked-in results

The checked-in output layout mirrors the specs under [`resources/evaluation/`](../evaluation/README.md). Regenerate these files with [`apps/evaluation`](../../apps/evaluation/README.md) when benchmark specs or runtime behavior change.
