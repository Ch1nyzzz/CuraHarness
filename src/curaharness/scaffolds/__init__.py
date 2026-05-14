"""Memory scaffold registry."""

from __future__ import annotations

from curaharness.scaffolds.base import MemoryScaffold, RetrievalMemoryScaffold, ScaffoldConfig, ScaffoldRun
from curaharness.scaffolds.bm25_scaffold import RankBM25Scaffold
from curaharness.scaffolds.mem0_scaffold import Mem0SourceScaffold
from curaharness.scaffolds.membank_scaffold import MemoryBankSourceScaffold
from curaharness.scaffolds.memgpt_scaffold import MemGPTSourceScaffold
from curaharness.scaffolds.no_memory_scaffold import NoMemoryScaffold


SCAFFOLD_REGISTRY: dict[str, type[MemoryScaffold]] = {
    RankBM25Scaffold.name: RankBM25Scaffold,
    Mem0SourceScaffold.name: Mem0SourceScaffold,
    MemGPTSourceScaffold.name: MemGPTSourceScaffold,
    MemoryBankSourceScaffold.name: MemoryBankSourceScaffold,
    NoMemoryScaffold.name: NoMemoryScaffold,
}

DEFAULT_EVOLUTION_SEED_SCAFFOLDS = (
    Mem0SourceScaffold.name,
    MemGPTSourceScaffold.name,
    MemoryBankSourceScaffold.name,
)

DEFAULT_BASELINE_SCAFFOLDS = (
    RankBM25Scaffold.name,
    *DEFAULT_EVOLUTION_SEED_SCAFFOLDS,
)

DEFAULT_MEMORY_SCAFFOLDS = DEFAULT_EVOLUTION_SEED_SCAFFOLDS

DEFAULT_SCAFFOLD_TOP_KS = {
    RankBM25Scaffold.name: 8,
    Mem0SourceScaffold.name: 30,
    MemGPTSourceScaffold.name: 12,
    MemoryBankSourceScaffold.name: 10,
    NoMemoryScaffold.name: 0,
}


def available_scaffolds() -> tuple[str, ...]:
    return tuple(sorted(SCAFFOLD_REGISTRY))


def build_scaffold(name: str) -> MemoryScaffold:
    try:
        return SCAFFOLD_REGISTRY[name]()
    except KeyError as exc:
        available = ", ".join(available_scaffolds())
        raise ValueError(f"unknown scaffold {name!r}; available: {available}") from exc


__all__ = [
    "MemoryScaffold",
    "RetrievalMemoryScaffold",
    "ScaffoldConfig",
    "ScaffoldRun",
    "DEFAULT_BASELINE_SCAFFOLDS",
    "DEFAULT_EVOLUTION_SEED_SCAFFOLDS",
    "DEFAULT_MEMORY_SCAFFOLDS",
    "DEFAULT_SCAFFOLD_TOP_KS",
    "available_scaffolds",
    "build_scaffold",
]
