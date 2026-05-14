#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

python -m curaharness.cli locomo prepare
python -m curaharness.cli evolve \
  --split train \
  --model "${CURAHARNESS_MODEL:-Qwen/Qwen3-8B}" \
  --base-url "${CURAHARNESS_BASE_URL:-http://127.0.0.1:8000/v1}" \
  --out "${CURAHARNESS_OUT:-runs/locomo_memory_seed_run}"
