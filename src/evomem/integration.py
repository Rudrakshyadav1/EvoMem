"""A tested boundary, not a claim of direct OpenHands integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .gating import gate
from .repository import MemoryRepository
from .retrieval import retrieve


@dataclass(frozen=True)
class AgentMemoryDecision:
    memory_id: str
    decision: str
    reasons: list[str]
    ranking_score: float


def memory_context(task: str, store: str, language: str | None = None, *, task_id: str | None = None, current_context: dict | None = None) -> dict:
    """Return only accepted memories for an agent adapter to inject as advisory context."""
    candidates = retrieve(task, MemoryRepository(store).list(), language)
    decisions = [(item, gate(item, current_context=current_context)) for item in candidates]
    accepted = [(item, decision) for item, decision in decisions if decision.decision == "accepted"]
    return {"task_id": task_id, "task": task, "accepted_memories": [{"memory_id": item.memory.memory_id, "summary": item.memory.solution,
              "warnings": decision.reasons} for item, decision in accepted], "decision_log": [asdict(AgentMemoryDecision(item.memory.memory_id, decision.decision, decision.reasons, item.score)) for item, decision in decisions],
            "abstained": not accepted}


def condition_memory_context(condition: str, task: str, store: str, language: str | None = None, *, task_id: str | None = None, current_context: dict | None = None) -> dict:
    """Create an ablation-specific context from a store pre-filtered by the manifest runner."""
    if condition == "no_memory":
        return {"task_id": task_id, "task": task, "accepted_memories": [], "decision_log": [], "abstained": True}
    candidates = retrieve(task, MemoryRepository(store).list(), language)
    if condition == "candidate_memory":
        selected = candidates
        reason = "Candidate-memory ablation; records are deliberately unvalidated."
    else:
        trusted = [item for item in candidates if item.memory.status == "validated"]
        if condition == "validated_semantic":
            selected = sorted(trusted, key=lambda item: (-item.scores["semantic_baseline"], item.memory.memory_id))
            reason = "Validated semantic-only ablation."
        elif condition == "validated_hybrid":
            selected = trusted
            reason = "Validated hybrid retrieval ablation without gate."
        elif condition == "validated_hybrid_gated":
            decisions = [(item, gate(item, current_context=current_context)) for item in trusted]
            selected = [item for item, decision in decisions if decision.decision == "accepted"]
            return {"task_id": task_id, "task": task, "accepted_memories": [{"memory_id": item.memory.memory_id, "summary": item.memory.solution,
                    "warnings": decision.reasons} for item, decision in decisions if decision.decision == "accepted"],
                    "decision_log": [asdict(AgentMemoryDecision(item.memory.memory_id, decision.decision, decision.reasons, item.score)) for item, decision in decisions], "abstained": not selected}
        else:
            raise ValueError(f"Unknown evaluation condition: {condition}")
    return {"task_id": task_id, "task": task, "accepted_memories": [{"memory_id": item.memory.memory_id, "summary": item.memory.solution,
            "warnings": [reason]} for item in selected], "decision_log": [asdict(AgentMemoryDecision(item.memory.memory_id, "supplied", [reason], item.score)) for item in selected], "abstained": not selected}
