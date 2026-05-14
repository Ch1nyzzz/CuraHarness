#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

python -m curaharness.cli locomo prepare

args=(
  --run-id "${CURAHARNESS_RUN_ID:-locomo_memory_opt}"
  --iterations "${CURAHARNESS_ITERATIONS:-20}"
  --split "${CURAHARNESS_SPLIT:-train}"
  --scaffold-extra-json "${CURAHARNESS_SCAFFOLD_EXTRA_JSON:-@configs/source_memory.example.json}"
  --model "${CURAHARNESS_MODEL:-Qwen/Qwen3-8B}"
  --base-url "${CURAHARNESS_BASE_URL:-http://127.0.0.1:8000/v1}"
  --claude-model "${CURAHARNESS_CLAUDE_MODEL:-claude-sonnet-4-6}"
)

if [[ -n "${CURAHARNESS_BASELINE_DIR:-}" ]]; then
  args+=(--baseline-dir "${CURAHARNESS_BASELINE_DIR}")
elif [[ -d runs/baselines ]]; then
  args+=(--baseline-dir runs/baselines)
fi

python -m curaharness.cli optimize "${args[@]}"
