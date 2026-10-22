"""Metrics only; never convert missing labels into failed outcomes."""
from __future__ import annotations


def _rate(records: list[dict], field: str, value: object = True) -> float | None:
    labelled = [record[field] for record in records if record.get(field) is not None]
    return None if not labelled else sum(item == value for item in labelled) / len(labelled)


def rates(records: list[dict]) -> dict[str, float | None]:
    false_accepts = [record for record in records if record.get("gate_decision") == "accepted" and record.get("negative_transfer") is not None]
    return {"task_success_rate": _rate(records, "success"), "negative_transfer_rate": _rate(records, "negative_transfer"),
            "gate_abstention_rate": _rate(records, "gate_decision", "abstained"),
            "retrieval_precision": _rate(records, "retrieved_relevant"),
            "false_acceptance_rate": _rate(false_accepts, "negative_transfer")}
