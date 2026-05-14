from pathlib import Path

from curaharness.optimization_cells import get_target_cells
from curaharness.proposer_prompt import build_progressive_proposer_prompt


def test_progressive_prompt_uses_workspace_summaries_and_reference_iterations():
    prompt = build_progressive_proposer_prompt(
        run_id="r",
        iteration=6,
        run_dir=Path("runs/r/proposer_calls/iter_006/workspace"),
        pending_eval_path=Path("runs/r/proposer_calls/iter_006/workspace/pending_eval.json"),
        summaries_dir=Path("runs/r/proposer_calls/iter_006/workspace/summaries"),
        reference_iterations_dir=Path(
            "runs/r/proposer_calls/iter_006/workspace/reference_iterations"
        ),
        generated_dir=Path("runs/r/proposer_calls/iter_006/workspace/generated"),
        source_snapshot_dir=Path("runs/r/proposer_calls/iter_006/workspace/source_snapshot"),
        budget="low",
        reference_iterations=(2, 3),
        target_system="memgpt",
        optimization_directions=("retrieval_policy: Improve evidence ranking.",),
        split="train",
        limit=0,
    )

    assert "summaries/evolution_summary.jsonl" in prompt
    assert "summaries/best_candidates.json" in prompt
    assert "summaries/candidate_score_table.json" in prompt
    assert "summaries/retrieval_diagnostics_summary.json" in prompt
    assert "summaries/diff_summary.jsonl" in prompt
    assert "CuraHarness Proposer" in prompt
    assert "Context budget" not in prompt
    assert "Context scope" not in prompt
    assert '"budget":' not in prompt
    assert "Optimization Focus" in prompt
    assert "mechanism directions" in prompt
    assert "retrieval_policy: Improve evidence ranking." in prompt
    assert "reference_iterations/" in prompt
    assert "iter_002, iter_003" in prompt
    assert "clean source snapshot" in prompt
    assert "diagnostic\nreferences only" in prompt
    assert "source parent" in prompt
    assert "UCB" not in prompt
    assert "bandit" not in prompt.lower()
    assert "parent_candidate_id" not in prompt
    assert '"reference_iterations": [2, 3]' in prompt
    assert "`candidate_results/**`" in prompt
    assert "build/database-construction logic" in prompt
    assert "amem_source_path" not in prompt
    assert "mem0_source_path" in prompt
    assert "fresh `source_base_dir`" in prompt
    assert "source bases" in prompt
    assert "expensive" in prompt


def test_progressive_prompt_requires_mechanism_changes_not_parameter_only():
    prompt = build_progressive_proposer_prompt(
        run_id="r",
        iteration=7,
        run_dir=Path("runs/r/proposer_calls/iter_007/workspace"),
        pending_eval_path=Path("runs/r/proposer_calls/iter_007/workspace/pending_eval.json"),
        summaries_dir=Path("runs/r/proposer_calls/iter_007/workspace/summaries"),
        reference_iterations_dir=Path(
            "runs/r/proposer_calls/iter_007/workspace/reference_iterations"
        ),
        generated_dir=Path("runs/r/proposer_calls/iter_007/workspace/generated"),
        source_snapshot_dir=Path("runs/r/proposer_calls/iter_007/workspace/source_snapshot"),
        budget="medium",
        reference_iterations=(1, 4, 5),
        target_system="memgpt",
        optimization_directions=(),
        split="train",
        limit=0,
    )

    assert "Parameter changes are allowed only as supporting details" in prompt
    assert "substantive change is only `top_k`, window size, thresholds" in prompt
    assert "Do not reduce recall solely to save tokens" in prompt
    assert "quality Pareto frontier over `passrate` and\n`average_score`" in prompt
    assert "Use gold answers only to classify failure\nmodes" in prompt
    assert "All copied project source under" in prompt
    assert "scaffolds, base classes, model/prompt helpers" in prompt
    assert "exactly one candidate" in prompt
    assert "top_k" in prompt
    assert '"top_k": [4, 8]' not in prompt


def test_default_prompt_uses_neutral_context_description():
    prompt = build_progressive_proposer_prompt(
        run_id="r",
        iteration=3,
        run_dir=Path("runs/r/proposer_calls/iter_003/workspace"),
        pending_eval_path=Path("runs/r/proposer_calls/iter_003/workspace/pending_eval.json"),
        summaries_dir=Path("runs/r/proposer_calls/iter_003/workspace/summaries"),
        reference_iterations_dir=Path(
            "runs/r/proposer_calls/iter_003/workspace/reference_iterations"
        ),
        generated_dir=Path("runs/r/proposer_calls/iter_003/workspace/generated"),
        source_snapshot_dir=Path("runs/r/proposer_calls/iter_003/workspace/source_snapshot"),
        budget="high",
        reference_iterations=(1, 2),
        target_system="memgpt",
        optimization_directions=(),
        split="train",
        limit=0,
        selection_policy="default",
    )

    assert "CuraHarness Proposer" in prompt
    assert "Context budget" not in prompt
    assert "Context scope" not in prompt
    assert '"budget":' not in prompt
    assert "Optimization Focus" not in prompt
    assert "mechanism directions" not in prompt
    assert "Cumulative summaries may mention iterations whose raw\n  bundles are not present here" in prompt


def test_random_recent_prompt_describes_baseline_reference_policy():
    common = {
        "run_id": "r",
        "iteration": 5,
        "run_dir": Path("runs/r/proposer_calls/iter_005/workspace"),
        "pending_eval_path": Path("runs/r/proposer_calls/iter_005/workspace/pending_eval.json"),
        "summaries_dir": Path("runs/r/proposer_calls/iter_005/workspace/summaries"),
        "reference_iterations_dir": Path(
            "runs/r/proposer_calls/iter_005/workspace/reference_iterations"
        ),
        "generated_dir": Path("runs/r/proposer_calls/iter_005/workspace/generated"),
        "source_snapshot_dir": Path("runs/r/proposer_calls/iter_005/workspace/source_snapshot"),
        "budget": "medium",
        "reference_iterations": (2, 3, 4),
        "target_system": "memgpt",
        "optimization_directions": (),
        "split": "train",
        "limit": 0,
    }

    random_prompt = build_progressive_proposer_prompt(
        **common,
        selection_policy="random",
    )
    recent_prompt = build_progressive_proposer_prompt(
        **common,
        selection_policy="recent",
    )

    assert "random sample of up to 3 previous" in random_prompt
    assert "most recent up to 3 previous" in recent_prompt
    assert "best iteration" not in random_prompt
    assert "worst iteration" not in recent_prompt

    best_prompt = build_progressive_proposer_prompt(
        **common,
        selection_policy="best",
    )
    assert "top-3 previous raw iterations by train passrate" in best_prompt
    assert "no worst iteration is exposed" in best_prompt


def test_miniswe_prompt_uses_coding_agent_schema_and_focus():
    cells = get_target_cells("mini_swe_agent_source")
    directions = tuple(
        f"{cell.name}: {cell.description} Focus areas: "
        f"{', '.join(cell.focus_functions) if cell.focus_functions else 'all functions'}. "
        f"Guidance: {cell.prompt_guidance}"
        for cell in cells
    )
    prompt = build_progressive_proposer_prompt(
        run_id="r",
        iteration=5,
        run_dir=Path("runs/r/proposer_calls/iter_005/workspace"),
        pending_eval_path=Path("runs/r/proposer_calls/iter_005/workspace/pending_eval.json"),
        summaries_dir=Path("runs/r/proposer_calls/iter_005/workspace/summaries"),
        reference_iterations_dir=Path(
            "runs/r/proposer_calls/iter_005/workspace/reference_iterations"
        ),
        generated_dir=Path("runs/r/proposer_calls/iter_005/workspace/generated"),
        source_snapshot_dir=Path("runs/r/proposer_calls/iter_005/workspace/source_snapshot"),
        budget="medium",
        reference_iterations=(1, 2, 3),
        target_system="mini_swe_agent_source",
        optimization_directions=directions,
        split="train",
        limit=30,
        benchmark_name="SWE-bench coding-agent issue resolution",
        raw_data_policy="SWE-bench gold patches, test patches, and evaluation results",
    )

    assert "optimizing the source-backed coding agent control loop" in prompt
    assert "memory layer for SWE-bench" not in prompt
    assert "issue_context: Optimize issue understanding" in prompt
    assert "patch_planning: Optimize the coding-agent loop" in prompt
    assert "verification_policy: Optimize when tests" in prompt
    assert "submission_recovery: Optimize final patch creation" in prompt
    assert '"scaffold_name": "mini_swe_agent_source"' in prompt
    assert "mini_swe_agent_source_source" not in prompt
    assert "primary editable mini-SWE-agent source tree" in prompt
    assert "edit `source_snapshot/candidate/upstream_source/mini-swe-agent/**`" in prompt
    assert (
        '"source_project_path": "source_snapshot/candidate/upstream_source/mini-swe-agent"'
        in prompt
    )
    assert "SWE-bench gold patches, test patches, and evaluation results" in prompt
    assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in prompt


def test_bandit_prompt_includes_context_policy_without_leaking_to_default():
    prompt = build_progressive_proposer_prompt(
        run_id="r",
        iteration=4,
        run_dir=Path("runs/r/proposer_calls/iter_004/workspace"),
        pending_eval_path=Path("runs/r/proposer_calls/iter_004/workspace/pending_eval.json"),
        summaries_dir=Path("runs/r/proposer_calls/iter_004/workspace/summaries"),
        reference_iterations_dir=Path(
            "runs/r/proposer_calls/iter_004/workspace/reference_iterations"
        ),
        generated_dir=Path("runs/r/proposer_calls/iter_004/workspace/generated"),
        source_snapshot_dir=Path("runs/r/proposer_calls/iter_004/workspace/source_snapshot"),
        budget="low",
        reference_iterations=(2,),
        target_system="memgpt",
        optimization_directions=("retrieval_policy: Improve evidence ranking.",),
        split="train",
        limit=0,
        selection_policy="bandit",
        bandit_policy={
            "trace_scope": "last1",
            "hot_files": ["summaries/candidate_score_table.json"],
            "warm_files": ["summaries/diff_summary.jsonl"],
            "cold_files": [],
            "best_iterations": [3],
            "worst_iteration": 1,
        },
    )

    assert "Bandit Context Policy" in prompt
    assert "`candidate_score_table.json`" in prompt
    assert "Hot files to inspect first" in prompt
    assert "`summaries/candidate_score_table.json`" in prompt
    assert "Other tracked files" in prompt
    assert "Cold files to avoid" not in prompt
    assert "Bandit reference roles" in prompt
    assert "iter_003" in prompt
    assert "iter_001" in prompt
