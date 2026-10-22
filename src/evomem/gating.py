from __future__ import annotations

from dataclasses import dataclass

from .retrieval import RetrievalResult
from .security import safety_warnings
from .versioning import compare_context

@dataclass(frozen=True)
class GateDecision:
    decision: str
    reasons: list[str]

def gate(result: RetrievalResult, minimum_score: float = .35, allow_partial: bool = False, current_context: dict | None = None) -> GateDecision:
    if result.memory.status == "quarantined":
        return GateDecision("rejected", ["Memory is quarantined."])
    if any(safety_warnings(claim.text) for claim in result.memory.claims):
        return GateDecision("rejected", ["Memory contains untrusted instruction-like content."])
    if current_context:
        compatibility = compare_context(result.memory.context, current_context)
        if compatibility.state == "incompatible":
            return GateDecision("rejected", compatibility.reasons)
        if compatibility.state == "warning":
            return GateDecision("abstained", compatibility.reasons)
    if result.memory.status != "validated" and not (allow_partial and result.memory.status == "partially_validated"):
        return GateDecision("abstained", ["Memory is not in the trusted pool."])
    if result.scores["language_compatibility"] == 0:
        return GateDecision("rejected", ["Language is incompatible."])
    if result.score < minimum_score:
        return GateDecision("abstained", [f"Score {result.score:.3f} is below threshold {minimum_score:.3f}."])
    return GateDecision("accepted", ["Trusted lifecycle status, compatible language, and ranking threshold met."])
