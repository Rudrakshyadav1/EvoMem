"""Metrics only; it deliberately does not fabricate agent benchmark results."""
from __future__ import annotations

def rates(records: list[dict]) -> dict[str, float | None]:
    if not records:
        return {"task_success_rate": None, "negative_transfer_rate": None, "gate_abstention_rate": None}
    n = len(records)
    return {"task_success_rate": sum(bool(r.get("success")) for r in records) / n,
            "negative_transfer_rate": sum(bool(r.get("negative_transfer")) for r in records) / n,
            "gate_abstention_rate": sum(r.get("gate_decision") == "abstained" for r in records) / n}
