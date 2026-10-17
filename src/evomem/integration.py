"""A tested boundary, not a claim of direct OpenHands integration."""
from __future__ import annotations

from .gating import gate
from .repository import MemoryRepository
from .retrieval import retrieve


def memory_context(task: str, store: str, language: str | None = None) -> dict:
    """Return only accepted memories for an agent adapter to inject as advisory context."""
    candidates = retrieve(task, MemoryRepository(store).list(), language)
    accepted = [item for item in candidates if gate(item).decision == "accepted"]
    return {"task": task, "accepted_memories": [{"memory_id": item.memory.memory_id, "summary": item.memory.solution,
                                                      "warnings": gate(item).reasons} for item in accepted],
            "abstained": not accepted}
