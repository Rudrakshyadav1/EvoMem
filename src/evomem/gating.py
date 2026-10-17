from __future__ import annotations

from dataclasses import dataclass

from .retrieval import RetrievalResult

@dataclass(frozen=True)
class GateDecision:
    decision: str
    reasons: list[str]

def gate(result: RetrievalResult, minimum_score: float = .35, allow_partial: bool = False) -> GateDecision:
    if result.memory.status == "quarantined":
        return GateDecision("rejected", ["Memory is quarantined."])
    if result.memory.status != "validated" and not (allow_partial and result.memory.status == "partially_validated"):
        return GateDecision("abstained", ["Memory is not in the trusted pool."])
    if result.scores["language_compatibility"] == 0:
        return GateDecision("rejected", ["Language is incompatible."])
    if result.score < minimum_score:
        return GateDecision("abstained", [f"Score {result.score:.3f} is below threshold {minimum_score:.3f}."])
    return GateDecision("accepted", ["Trusted lifecycle status, compatible language, and ranking threshold met."])
