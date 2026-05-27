#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

if ! git -C / config --global --fixed-value --get-all safe.directory "$WORKSPACE_DIR" >/dev/null; then
	git -C / config --global --add safe.directory "$WORKSPACE_DIR"
fi

cd "$WORKSPACE_DIR"

direnv allow "$WORKSPACE_DIR"
sudo install -d -m 755 -o vscode -g vscode "$WORKSPACE_DIR/.cache"
sudo install -d -m 755 -o vscode -g vscode "$WORKSPACE_DIR/.cache/uv"
