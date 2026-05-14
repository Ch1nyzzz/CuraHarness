# Repository Guidelines

## Project structure and module organization

CuraHarness is a Python 3.11 `src`-layout package. Core package code lives in
`src/curaharness/`; memory scaffold implementations are under
`src/curaharness/scaffolds/`, and small helpers live in
`src/curaharness/utils/`. Tests are in `tests/` and mirror major modules such
as `test_optimizer.py`, `test_pareto.py`, and `test_scaffolds.py`. CLI and
experiment helpers are in `scripts/`. Configuration examples are in
`configs/`. Runtime outputs belong in `runs/` and `logs/`; do not treat
generated run artifacts as source changes. External reference checkouts are
expected under `references/vendor/`.

## Build, test, and development commands

Install the editable package with development dependencies:

```bash
python -m pip install -e '.[dev]'
```

Install source-backed scaffold dependencies when working on mem0, MemGPT, or
MemoryBank integrations:

```bash
python -m pip install -e '.[dev,source]'
scripts/fetch_reference_repos.sh
```

Run the test suite:

```bash
pytest -q
```

Run a quick dry-run optimization smoke test:

```bash
curaharness optimize --run-id smoke_opt --iterations 1 --limit 3 --dry-run \
  --scaffold-extra-json @configs/source_memory.example.json
```

## Coding style and naming conventions

Use 4-space indentation, type hints, and small focused functions. Follow the
existing module style: dataclasses for configuration records, snake_case for
functions and variables, PascalCase for classes, and descriptive test names.
Prefer `pathlib.Path` for filesystem work and structured JSON/YAML parsing
over ad hoc string parsing. Keep generated candidate code under run-local
`generated/` directories, not `src/`.

## Testing guidelines

Pytest is the only configured test framework. Add or update tests beside the
behavior you change, using filenames `tests/test_<feature>.py` and test
functions named `test_<expected_behavior>`. For optimizer, prompt, dynamic
loading, and scaffold changes, include regression tests that exercise file
paths and serialized JSON payloads. Run `pytest -q` before handing off
changes.

## Security and configuration tips

Do not commit secrets, model API keys, local cache paths, or large generated
outputs. Source-backed scaffolds may depend on local model endpoints and
vendor repositories; document non-default paths in the PR description rather
than hardcoding them.

For `claude-kimi` / Kimi proposer runs, read the Kimi/Moonshot credential key
from environment variables, not from an interactive login or a mounted
`~/.kimi` directory. If a repo-local `.env` exists, source it before launching
the run: `set -a && source .env && set +a`. When using the Docker proposer
sandbox, explicitly pass the credential variable with `--proposer-docker-env`,
at minimum `KIMI_API_KEY` or `MOONSHOT_API_KEY` as available.

### Docker image selection for the proposer sandbox

- For `--proposer-agent kimi` with docker, always use
  `--proposer-docker-image docker-claude-kimi:latest` (not
  `docker-claude:latest`). The `docker-claude-kimi` image has `claude-kimi`
  pre-installed and sets `ANTHROPIC_AUTH_TOKEN` from `KIMI_API_KEY`, so no
  `.claude.json` is needed. Set `--proposer-docker-home /tmp` and pass
  `--proposer-docker-env KIMI_API_KEY`. Full example:

  ```bash
  curaharness optimize --locomo \
    --proposer-agent kimi --selection-policy bandit \
    --proposer-sandbox docker \
    --proposer-docker-image docker-claude-kimi:latest \
    --proposer-docker-home /tmp \
    --proposer-docker-env KIMI_API_KEY \
    ...
  ```

- For `--proposer-agent claude` with docker, use
  `--proposer-docker-image docker-claude:latest` and mount the host Claude
  credentials read-only at the in-container home path:

  ```bash
  --proposer-docker-home "$HOME" \
  --proposer-docker-mount "$HOME/.claude:$HOME/.claude:ro" \
  --proposer-docker-mount "$HOME/.claude.json:$HOME/.claude.json:ro"
  ```

- Never use `docker-claude:latest` plus a mounted `claude-kimi` binary for
  kimi runs; that image has no `.claude.json` so Claude Code inside the
  container will fail to authenticate.

## Running test evaluations for a completed train run

Use `scripts/evaluate_candidate_json.py` with a candidate spec JSON derived
from the train run's `best_candidates.json`:

```python
# build spec JSON (run once to produce runs/<out>/candidate_spec.json)
import json, pathlib

best_cands = json.loads(
    pathlib.Path("runs/<train_run>/best_candidates.json").read_text()
)
cands = best_cands if isinstance(best_cands, list) else best_cands.get("candidates", [])
best = max(cands, key=lambda c: c.get("score", c.get("passrate", 0)))
spec = {
    "name": best["scaffold_name"],
    "scaffold_name": "memgpt_source",
    "candidate_id": "<prefix>_" + best["candidate_id"],
    "top_k": best["config"]["top_k"],
    "window": best["config"]["window"],
    "extra": best["config"]["extra"],
    "source_family": "memgpt",
}
pathlib.Path("runs/<out>/candidate_spec.json").write_text(json.dumps(spec, indent=2))
```

Then evaluate:

```bash
nohup python3 scripts/evaluate_candidate_json.py \
  --candidate-json runs/<out>/candidate_spec.json \
  --out runs/<out> --split test --eval-workers 128 \
  --model "${CURAHARNESS_MODEL:-Qwen/Qwen3-8B}" \
  --base-url "${CURAHARNESS_BASE_URL:-http://127.0.0.1:8000/v1}" \
  > logs/<out>.log 2>&1 &
```

For long-running optimizer jobs that must survive the current session, launch
them with `setsid ... > logs/<name>.log 2>&1 < /dev/null &` rather than plain
`nohup`. In this environment, `setsid` is the reliable way to detach the
process so it stays running with `PPID=1`.
