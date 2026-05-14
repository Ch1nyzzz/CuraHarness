"""Prompt builder for proposer iterations."""

from __future__ import annotations

from pathlib import Path


def _optimization_subject(target_system: str) -> str:
    """Return a short phrase for what the proposer is optimizing."""

    normalized = target_system.lower()
    if normalized in {"mini_swe_agent_source", "mini_swe_agent", "minisweagent"}:
        return "source-backed coding agent control loop"
    return "memory layer"


def _candidate_scaffold_name(target_system: str) -> str:
    """Return the scaffold/agent name shown in the candidate JSON example."""

    if target_system.lower().endswith("_source"):
        return target_system
    return f"{target_system}_source"


def _default_source_project_path(source_snapshot_dir: Path, target_system: str) -> str:
    """Return the source path candidates should point at in pending_eval.json."""

    if target_system.lower() in {"mini_swe_agent_source", "mini_swe_agent", "minisweagent"}:
        return f"{source_snapshot_dir}/candidate/upstream_source/mini-swe-agent"
    return f"{source_snapshot_dir}/candidate/project_source"


def build_progressive_proposer_prompt(
    *,
    run_id: str,
    iteration: int,
    run_dir: Path,
    pending_eval_path: Path,
    summaries_dir: Path,
    reference_iterations_dir: Path,
    generated_dir: Path,
    source_snapshot_dir: Path,
    budget: str,
    reference_iterations: tuple[int, ...],
    target_system: str,
    optimization_directions: tuple[str, ...],
    split: str,
    limit: int,
    selection_policy: str = "progressive",
    bandit_policy: dict[str, object] | None = None,
    benchmark_name: str = "LOCOMO conversational-memory QA",
    raw_data_policy: str = "raw LOCOMO data",
    progressive_best_count: int | None = None,
) -> str:
    """Build the proposer prompt for scoped progressive-context runs."""

    direction_lines = "\n".join(f"- {line}" for line in optimization_directions)
    focus_section = ""
    if direction_lines:
        focus_section = f"""
## Optimization Focus

You may choose one of these mechanism directions, combine them, or make an
overall system-level redesign:

{direction_lines}
"""

    workspace_dir = run_dir

    def show(path: Path) -> str:
        try:
            return str(path.relative_to(workspace_dir))
        except ValueError:
            return str(path)

    refs = ", ".join(f"iter_{item:03d}" for item in reference_iterations) or "none"
    if selection_policy == "progressive" and budget in {"low", "medium"}:
        if progressive_best_count is None:
            best_count = 3 if budget == "medium" else 1
        else:
            best_count = max(0, int(progressive_best_count))
        best_refs = reference_iterations[:best_count]
        worst_refs = reference_iterations[best_count:]
        best_label = ", ".join(f"iter_{item:03d}" for item in best_refs) or "none"
        worst_label = ", ".join(f"iter_{item:03d}" for item in worst_refs) or "none"
        reference_role_note = (
            f"- Progressive reference roles: best iteration(s): `{best_label}`; "
            f"worst iteration: `{worst_label}`.\n"
        )
    elif selection_policy == "progressive":
        reference_role_note = (
            "- Progressive reference roles: high budget includes all available raw "
            "reference iterations; use summaries to identify best and worst.\n"
        )
    elif selection_policy == "bandit" and bandit_policy:
        best_iter_list = bandit_policy.get("best_iterations") or []
        worst_iter_value = bandit_policy.get("worst_iteration")
        best_label = (
            ", ".join(f"iter_{int(item):03d}" for item in best_iter_list)
            if best_iter_list
            else "none"
        )
        worst_label = (
            f"iter_{int(worst_iter_value):03d}"
            if isinstance(worst_iter_value, int)
            else "none"
        )
        reference_role_note = (
            f"- Bandit reference roles: best iteration(s): `{best_label}`; "
            f"worst iteration: `{worst_label}`.\n"
        )
    elif selection_policy == "random":
        reference_role_note = (
            "- Baseline reference policy: random sample of up to 3 previous "
            "raw iterations; no metric ranking is implied by the selection.\n"
        )
    elif selection_policy == "recent":
        reference_role_note = (
            "- Baseline reference policy: most recent up to 3 previous raw "
            "iterations; no metric ranking is implied by the selection.\n"
        )
    elif selection_policy == "best":
        reference_role_note = (
            "- Baseline reference policy: top-3 previous raw iterations by "
            "train passrate; no worst iteration is exposed.\n"
        )
    else:
        reference_role_note = ""
    bandit_section = ""
    if selection_policy == "bandit":
        policy = bandit_policy or {}

        def listed(name: str) -> str:
            values = policy.get(name)
            if not isinstance(values, (list, tuple)) or not values:
                return "none"
            return ", ".join(f"`{item}`" for item in values[:12])

        trace_scope = str(policy.get("trace_scope") or "last1")
        bandit_section = f"""
## Bandit Context Policy

This iteration uses online file-utility estimates to suggest where to start.
Begin with the compact summaries (`candidate_score_table.json`,
`retrieval_diagnostics_summary.json`, `diff_summary.jsonl`). Read
`evolution_summary.jsonl` and `best_candidates.json` whenever you need to trace
cross-iteration patterns or identify a strong parent to build on.

The hot/other lists below are advisory and reflect historical reads only;
they do not restrict what you may read. If a file under "Other tracked files"
fills a diagnostic gap, read it.

- Trace scope: `{trace_scope}`
- Hot files to inspect first: {listed("hot_files")}
- Other tracked files (read on demand if they fill a diagnostic gap): {listed("warm_files")}
"""
    refs_json = ", ".join(str(item) for item in reference_iterations)
    pending_eval_display = show(pending_eval_path)
    summaries_display = show(summaries_dir)
    reference_display = show(reference_iterations_dir)
    source_snapshot_display = show(source_snapshot_dir)
    generated_display = show(generated_dir)
    optimization_subject = _optimization_subject(target_system)
    candidate_scaffold_name = _candidate_scaffold_name(target_system)
    default_source_project_path = _default_source_project_path(
        Path(source_snapshot_display),
        target_system,
    )
    is_mini_swe_agent = target_system.lower() in {
        "mini_swe_agent_source",
        "mini_swe_agent",
        "minisweagent",
    }
    source_path_note = (
        "`extra.source_project_path` must point to the edited mini-SWE-agent "
        "snapshot under `source_snapshot/candidate/upstream_source/mini-swe-agent`."
        if is_mini_swe_agent
        else "`extra.source_project_path` must point to the edited snapshot project source "
        "when files under `project_source/src/curaharness` are modified."
    )
    mini_swe_source_note = (
        f"- `{source_snapshot_display}/candidate/upstream_source/mini-swe-agent/` — "
        "primary editable mini-SWE-agent source tree for coding-agent mechanisms.\n"
        if is_mini_swe_agent
        else ""
    )
    mini_swe_edit_note = (
        "\nFor mini-SWE-agent candidates, edit "
        f"`{source_snapshot_display}/candidate/upstream_source/mini-swe-agent/**` "
        "for agent control-loop, prompt/config, action parsing, verification, or "
        "submission behavior, and point `extra.source_project_path` at that tree.\n"
        if is_mini_swe_agent
        else ""
    )

    return f"""# CuraHarness Proposer — iteration {iteration}

You are optimizing the {optimization_subject} for {benchmark_name}.

Run exactly one iteration. The outer CuraHarness harness will import and evaluate
the candidate after this session exits. Do not run the full harness evaluation.

## Assignment

- Run id: `{run_id}`
- Target system: `{target_system}`
- Eval split: `{split}`
- Eval limit: `{limit}` (`0` means full split)
- Cumulative summaries: `{summaries_display}/`
- Raw reference iterations: `{reference_display}/` ({refs})
{reference_role_note}
- Writable clean source snapshot: `{source_snapshot_display}/candidate/`
- Generated wrapper directory: `{generated_display}/`
- Required output: `{pending_eval_display}`

Every iteration starts from the clean source snapshot in
`{source_snapshot_display}/candidate/`. Historical iterations are diagnostic
references only. Do not treat any reference iteration as a source parent and do
not mechanically copy a prior candidate; implement one intentional mechanism
from the clean source.

## Objective

Primary objective: expand the quality Pareto frontier over `passrate` and
`average_score`.

Optimize both pass/fail reliability and partial-answer quality. `passrate` is
the primary final metric, but `average_score` is an optimization objective
because it captures near misses and often tracks generalization better than a
single threshold. `token_consuming` is a reported diagnostic, not an objective.
Do not reduce recall solely to save tokens. Compression, filtering, reranking,
and context budgeting are valid when they are expected to improve answer
quality by removing noise or surfacing stronger evidence.

Optimize for expected generalization, not the reported training split alone.
Use raw task traces to identify failure modes, recurring evidence gaps, and
bad evidence-ordering behavior. Do not use traces to create answer-surface
patches, scorer-specific strings, annotation typo fixes, or deterministic
shortcuts for known saved tasks. Use gold answers only to classify failure
modes; do not encode task-specific answers, names, dates, or scorer quirks into
runtime behavior.

{focus_section}
{bandit_section}

## Available Files

- `{summaries_display}/evolution_summary.jsonl` — full cumulative event history
  through the previous iteration.
- `{summaries_display}/best_candidates.json` — current passrate/average_score
  quality Pareto frontier candidates.
- `{summaries_display}/candidate_score_table.json` — compact metrics for all
  evaluated candidates.
- `{summaries_display}/retrieval_diagnostics_summary.json` — cumulative failure
  and retrieval-pattern summary.
- `{summaries_display}/iteration_index.json` — paths for prior iteration
  artifacts.
- `{summaries_display}/diff_summary.jsonl` — compact source-change records.
- `{reference_display}/` — raw iteration bundles copied into this workspace for
  detailed diagnosis. Cumulative summaries may mention iterations whose raw
  bundles are not present here.
- `{source_snapshot_display}/candidate/project_source/src/curaharness/` — editable
  project source for this candidate.
- `{source_snapshot_display}/candidate/original_project_source/src/curaharness/` —
  clean project source used for diffing and policy checks.
- `{source_snapshot_display}/candidate/upstream_source/` — copied upstream
  source when available.
{mini_swe_source_note}
- `{generated_display}/` — optional importable wrapper modules for this
  iteration.

Do not read global run directories, global `candidate_results`, repo-root
`src/`, `references/vendor`, {raw_data_policy}, or CuraHarness scoring helpers.
Candidate runtime code must not access benchmark raw data, `candidate_results/**`,
or `curaharness.metrics.score_prediction`.
The copied `curaharness` package is intentionally benchmark-scoped and incomplete.
Do not add runtime imports from repo-root harness modules such as
`curaharness.evaluation`, `curaharness.pareto`, `curaharness.metrics`, optimizer modules,
or any module not listed in Available Files. Keep `curaharness/__init__.py`
minimal; do not make it import top-level repository APIs.

## Edit Scope

You may edit only:

- `{source_snapshot_display}/candidate/**`
- `{generated_display}/**`
- `{pending_eval_display}`

All copied project source under
`{source_snapshot_display}/candidate/project_source/src/curaharness/**` is editable
for this candidate, including scaffolds, base classes, model/prompt helpers,
dynamic-loading helpers, and utils.
{mini_swe_edit_note}

Source-backed baseline memories and source bases are read-only and expensive
to rebuild. If your source edit changes build/database-construction logic or
other persisted memory construction semantics, use a fresh `source_base_dir`
and a new stable `build_tag`. For upstream source edits, route explicit paths
such as `mem0_source_path` through the copied source snapshot.

## Quality Gate

Before writing `pending_eval.json`, verify that the candidate is a real
mechanism change, is not just a `top_k`/`window`/threshold/weight variant, does
not use gold answers at inference time, does not hardcode benchmark-specific
answers, and uses the isolated source snapshot for source edits.
Parameter changes are allowed only as supporting details of a mechanism change.
A candidate whose substantive change is only `top_k`, window size, thresholds,
weights, prompt length, or context budget will be rejected.
Run a lightweight syntax/import smoke check against the edited snapshot before
writing `pending_eval.json`; do not run the full harness evaluation.

## Required Output

Write exactly this JSON file:
`{pending_eval_display}`

Schema:

```json
{{
  "candidates": [
    {{
      "name": "short_unique_name",
      "scaffold_name": "{candidate_scaffold_name}",
      "top_k": 8,
      "window": 1,
      "source_family": "{target_system}",
      "reference_iterations": [{refs_json}],
      "build_tag": "stable_build_identifier",
      "source_snapshot_path": "{source_snapshot_display}",
      "extra": {{
        "source_project_path": "{default_source_project_path}"
      }},
      "hypothesis": "why this should improve passrate and/or average_score",
      "changes": "brief implementation summary"
    }}
  ]
}}
```

Notes:

- The `candidates` array must contain exactly one candidate.
- `top_k` must be a single integer.
- Use a source-backed scaffold such as `{candidate_scaffold_name}` when editing the copied
  scaffold source.
- {source_path_note}
- If you create a wrapper module in `{generated_display}`, keep it small and
  route source-backed mechanisms through the clean edited snapshot.
- `reference_iterations` records the raw bundles available for diagnosis; it is
  not a parent list.
"""
