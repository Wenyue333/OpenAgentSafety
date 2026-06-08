#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "$(basename "${SCRIPT_DIR}")" != "evaluation" ]]; then
  echo "Error: run_opencode_eval.sh must live in the evaluation directory" >&2
  exit 1
fi

cd "${REPO_ROOT}"
python evaluation/opencode_runner.py "$@"
