# Analysis

Collects evaluation output into normalized CSV files and writes report-ready analysis CSV files.

## Usage

Collect a dataset from checked-in evaluation results and the matching SQLite database:

```bash
bazel run //apps/analysis:main -- collect \
  --evaluation-results-dir resources/evaluation-results \
  --database-path resources/evaluation-results/backend.sqlite3 \
  --output-dir resources/analysis/collected
```

Write report CSV files from a collected dataset:

```bash
bazel run //apps/analysis:main -- report \
  --collection-dir resources/analysis/collected \
  --output-dir resources/analysis/report
```

## Outputs

Collection outputs:

- `manifest.yaml`: collected database hash plus benchmark conditions
- `conditions.csv`: one row per condition with its `click_delay_ms`
- `worker-runs.csv`: one run-duration row per benchmark worker
- `trials.csv`: one row per recorded trial latency with raw evaluator timing fields

Report outputs:

- `manifest.yaml`: copied collection manifest
- `analysis-overview.csv`: one-row derived report summary
- `analysis-conditions.csv`: condition-level summary for report tables
- `analysis-full.csv`: per-worker detailed summary for report reference

The checked-in examples live under [`resources/analysis/`](../../resources/analysis/README.md).
