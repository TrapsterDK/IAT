#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

cd "$WORKSPACE_DIR"

bazel run --config=ai //tools:env || true
