# CuraHarness

Reference implementation for **CuraHarness: Online Context Curation for
Automated Harness Optimization**.

CuraHarness inserts an online context-curation loop into the standard
propose–evaluate workflow used by automated harness optimizers. Two curation
stages share the same bounded inspection budget:

- **Iteration-level curation** (`CuraHarness-Iter`) selects which prior
  iterations and traces are exposed to the proposer, using a low → medium →
  high tier schedule driven by stagnation of the frontier-improvement signal.
- **File-level delayed-credit curation** (`CuraHarness-Full`) ranks files
  inside the curated workspace by a UCB-style utility that combines reward
  attributed to past read events, exploration of rarely read files, and a cost
  penalty.

The same outer loop supports the **full-context baseline** (no curation) and
both CuraHarness variants, so all three policies are evaluated with identical
proposer/evaluator code paths.

## Repository layout

```
src/curaharness/        # core package
  optimizer.py          # outer propose–evaluate loop (shared skeleton)
  locomo_optimizer.py   # LoCoMo-specific evaluation
  longmemeval_optimizer.py
  optimization_cells.py # default / progressive / bandit selection policies
  evaluation.py         # candidate scoring + caching
  pareto.py             # passrate / token-cost frontier
  claude_runner.py      # coding-agent proposer driver (claude / kimi / codex)
  scaffolds/            # built-in memory scaffolds (bm25 / mem0 / memgpt / membank)
  source_base.py        # source-backed scaffold helpers
  benchmark_tasks.py    # LoCoMo / LongMemEval / SWE-bench task specs
  benchmark_workspaces.py
  cli.py                # `curaharness ...` CLI entry point
configs/                # default config and source-memory example
data/                   # LoCoMo and LongMemEval splits + seed data
docs/
  PIPELINE.md           # end-to-end walk-through of the optimizer
  EXPERIMENT_INSIGHTS.md
  experiment_detail.md
scripts/                # launch and evaluation helpers
tests/                  # pytest suite
```

## Install

The package is editable-installable under Python 3.11+:

```bash
python -m pip install -e '.[dev]'
```

For source-backed memory scaffolds (mem0 / MemGPT / MemoryBank), install the
optional `source` extras and fetch the upstream repos:

```bash
python -m pip install -e '.[dev,source]'
scripts/fetch_reference_repos.sh
```

## Models and endpoints

The inner harness on memory benchmarks is a MemGPT-style memory agent driven
by an OpenAI-compatible local model. The defaults assume

- `model`: `Qwen/Qwen3-8B`
- `base_url`: `http://127.0.0.1:8000/v1`

Override either with the matching CLI flag, the `CURAHARNESS_MODEL` /
`CURAHARNESS_BASE_URL` environment variables, or by editing `configs/default.yaml`.

The outer proposer can be invoked in three modes:

- `--proposer-agent claude` — Claude Code-style coding agent.
- `--proposer-agent codex` — Codex-style coding agent (paper: `codex54`,
  with GPT-5.4).
- `--proposer-agent kimi` — Kimi via the `claude-kimi` shim (paper:
  `claudekimi`, with Kimi K2.6); recommended inside the Docker sandbox image
  `docker-claude-kimi:latest`.

Proposer authentication is read from environment variables (e.g.,
`KIMI_API_KEY`, `MOONSHOT_API_KEY`, `TOGETHER_API_KEY` for the LongMemEval
judge). The repo never reads credentials from interactive logins.

## Prepare benchmarks

LoCoMo (cached locally if `~/.cache/curaharness/locomo10.json` exists,
otherwise downloaded with `--allow-download`):

```bash
curaharness locomo prepare --allow-download
```

LongMemEval (cleaned LongMemEval-S from Hugging Face):

```bash
curaharness longmemeval prepare --variant s --allow-download
```

SWE-bench Verified uses the standard `trainfirst30` / verified test split; see
`docs/PIPELINE.md` for the loader.

## Reproduce paper experiments

Each policy below is run with the same outer loop. The three policies differ
only at two points: (i) how each iteration picks its budget / reference
iterations / file hints, and (ii) what state it writes back after evaluation.

### Full-context baseline

```bash
curaharness optimize \
  --run-id locomo_memgpt_claudekimi_fullcontext \
  --locomo --iterations 30 --split train \
  --scaffolds memgpt_source \
  --scaffold-extra-json @configs/source_memory.example.json \
  --eval-workers 128 \
  --proposer-agent kimi --selection-policy default \
  --proposer-sandbox docker \
  --proposer-docker-image docker-claude-kimi:latest \
  --proposer-docker-env KIMI_API_KEY \
  --proposer-docker-home /tmp
```

### CuraHarness-Iter (iteration-level curation only)

Adds the `low → medium → high` historical-scope schedule from Section 4.1 of
the paper:

```bash
curaharness optimize \
  --run-id locomo_memgpt_claudekimi_curaharness_iter \
  --locomo --iterations 30 --split train \
  --scaffolds memgpt_source \
  --scaffold-extra-json @configs/source_memory.example.json \
  --eval-workers 128 \
  --proposer-agent kimi --selection-policy progressive \
  --proposer-sandbox docker \
  --proposer-docker-image docker-claude-kimi:latest \
  --proposer-docker-env KIMI_API_KEY \
  --proposer-docker-home /tmp
```

### CuraHarness-Full (iteration + file-level delayed-credit curation)

Adds the file-level UCB-style utility from Section 4.3:

```bash
curaharness optimize \
  --run-id locomo_memgpt_claudekimi_curaharness_full \
  --locomo --iterations 30 --split train \
  --scaffolds memgpt_source \
  --scaffold-extra-json @configs/source_memory.example.json \
  --eval-workers 128 \
  --proposer-agent kimi --selection-policy bandit \
  --proposer-sandbox docker \
  --proposer-docker-image docker-claude-kimi:latest \
  --proposer-docker-env KIMI_API_KEY \
  --proposer-docker-home /tmp
```

Swap `--locomo` for `--longmemeval` to switch benchmarks, and
`--proposer-agent kimi` for `--proposer-agent codex` (with the appropriate
docker image and credentials) to switch from `claudekimi` to `codex54`.

A completed train run can be re-evaluated on the held-out test split with
`scripts/evaluate_candidate_json.py`. See `AGENTS.md` for the exact recipe.

### SWE-bench Verified

The SWE-bench setup uses a fixed Mini-SWE agent driven by DeepSeek v4 Flash as
the inner solver, with `claudekimi` as the outer proposer:

```bash
curaharness optimize \
  --run-id swebench_claudekimi_curaharness_full \
  --task swebench --swebench-split trainfirst30 \
  --iterations 20 \
  --proposer-agent kimi --selection-policy bandit \
  --proposer-sandbox docker \
  --proposer-docker-image docker-claude-kimi:latest \
  --proposer-docker-env KIMI_API_KEY \
  --proposer-docker-home /tmp
```

## Outputs

Every run writes a structured directory under `runs/<run-id>/`:

- `candidate_results/*.json` — per-candidate scores
- `best_candidates.json` — running top-1 by train passrate
- `evolution_summary.jsonl` — iteration-level events (proposer + evaluator)
- `progressive_state.json` / `bandit_state.json` — policy state
- `proposer_calls/iter_<NNN>/{workspace,source_snapshot,eval}` — the exact
  context shown to the proposer at each iteration, the source snapshot it
  edited, and the resulting evaluation
- `pareto_frontier.json` — passrate × token-cost frontier

The first three are sufficient to reproduce Table 1 and Figure 2 from the
paper.

## Documentation

- `docs/PIPELINE.md` — end-to-end walk-through of the optimizer, the three
  selection policies, and how to add a new one.
- `docs/EXPERIMENT_INSIGHTS.md` — cross-run observations about where
  breakthroughs occur across budget tiers.
- `docs/experiment_detail.md` — per-cell experiment table grouped by
  benchmark, proposer, and policy family.
