from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .schemas import Memory


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_+#.-]+", text.lower()))


def serialize(memory: Memory) -> str:
    return " ".join([memory.task.get("description", ""), memory.task.get("language", ""), memory.task.get("domain", ""),
                     memory.solution.get("approach", ""), *memory.solution.get("key_ideas", []), *(c.text for c in memory.claims)])


@dataclass
class RetrievalResult:
    memory: Memory
    scores: dict[str, float]
    score: float
    reasons: list[str]


def retrieve(query: str, memories: list[Memory], language: str | None = None, top_k: int = 5) -> list[RetrievalResult]:
    query_tokens = tokens(query)
    results = []
    for memory in memories:
        memory_tokens = tokens(serialize(memory))
        lexical = len(query_tokens & memory_tokens) / len(query_tokens | memory_tokens) if query_tokens | memory_tokens else 0.0
        semantic = (2 * len(query_tokens & memory_tokens) / (len(query_tokens) + len(memory_tokens))) if query_tokens | memory_tokens else 0.0
        compatible = 1.0 if language and memory.task.get("language", "").lower() == language.lower() else 0.5 if not language else 0.0
        quality = 1.0 if memory.status == "validated" else 0.5 if memory.status == "partially_validated" else 0.0
        score = .45 * semantic + .35 * lexical + .1 * compatible + .1 * quality
        results.append(RetrievalResult(memory, {"semantic_baseline": semantic, "lexical_jaccard": lexical,
                                                 "language_compatibility": compatible, "validation_quality": quality}, score,
                                       ["token overlap", "language compatibility", f"lifecycle={memory.status}"]))
    return sorted(results, key=lambda item: (-item.score, item.memory.memory_id))[:top_k]
