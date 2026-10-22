from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .evaluation import rates

CONDITIONS = ("no_memory", "candidate_memory", "validated_semantic", "validated_hybrid", "validated_hybrid_gated")

@dataclass(frozen=True)
class EvaluationTask:
    task_id: str
    repository: str
    order: int
    language: str | None = None

@dataclass(frozen=True)
class EvaluationPlanItem:
    task_id: str
    repository: str
    order: int
    condition: str
    eligible_prior_task_ids: list[str]
    language: str | None = None

@dataclass(frozen=True)
class EvaluationRecord:
    task_id: str
    condition: str
    success: bool | None
    gate_decision: str | None
    negative_transfer: bool | None
    memory_ids: list[str]
    note: str = ""
    retrieved_relevant: bool | None = None
    source_task_ids: list[str] | None = None


def load_tasks(path: str | Path) -> list[EvaluationTask]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = raw.get("tasks", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise ValueError("Evaluation dataset must be a task list or an object with a tasks list.")
    tasks = [EvaluationTask(**entry) for entry in entries]
    seen = set()
    for task in tasks:
        key = (task.repository, task.order)
        if not task.task_id or task.order < 0: raise ValueError("Task IDs must be nonempty and order must be non-negative.")
        if task.task_id in seen: raise ValueError(f"Duplicate task ID: {task.task_id}")
        seen.add(task.task_id)
        if sum(1 for item in tasks if (item.repository, item.order) == key) != 1:
            raise ValueError(f"Duplicate chronological order in repository: {key}")
    return tasks


def build_plan(tasks: list[EvaluationTask]) -> list[EvaluationPlanItem]:
    plan: list[EvaluationPlanItem] = []
    for task in sorted(tasks, key=lambda item: (item.repository, item.order, item.task_id)):
        eligible = [item.task_id for item in tasks if item.repository == task.repository and item.order < task.order]
        for condition in CONDITIONS:
            # The no-memory arm never gets a memory, even if prior tasks exist.
            plan.append(EvaluationPlanItem(task.task_id, task.repository, task.order, condition, [] if condition == "no_memory" else eligible, task.language))
    return plan


def write_manifest(plan: list[EvaluationPlanItem], output: str | Path, *, agent: str, model: str, seed: int | None, budget: dict) -> dict:
    """A frozen run specification; executing agents is deliberately an external adapter concern."""
    payload = {"schema_version": "1.0", "agent": agent, "model": model, "seed": seed, "budget": budget,
               "runs": [asdict(item) for item in plan], "rules": {"same_agent_model_budget_per_condition": True, "chronological_memory_only": True}}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_and_validate_records(path: str | Path, plan: list[EvaluationPlanItem]) -> list[EvaluationRecord]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = raw.get("results", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise ValueError("Evaluation results must be a list or an object containing results.")
    allowed = {(item.task_id, item.condition): item for item in plan}
    records = [EvaluationRecord(**entry) for entry in entries]
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (record.task_id, record.condition)
        if key not in allowed: raise ValueError(f"Result is not in the evaluation plan: {key}")
        if key in seen: raise ValueError(f"Duplicate result for planned run: {key}")
        seen.add(key)
        item = allowed[key]
        if record.condition == "no_memory" and record.memory_ids:
            raise ValueError("No-memory condition cannot record supplied memory IDs.")
        if record.source_task_ids:
            unexpected = set(record.source_task_ids) - set(item.eligible_prior_task_ids)
            if unexpected: raise ValueError(f"Result leaks future/cross-repository tasks: {sorted(unexpected)}")
    return records


def write_report(records: list[EvaluationRecord], output: str | Path, plan: list[EvaluationPlanItem] | None = None) -> dict:
    payload = {"conditions": CONDITIONS, "plan": [asdict(item) for item in (plan or [])], "results": [asdict(r) for r in records], "metrics": rates([asdict(r) for r in records]),
               "limitation": "Metrics are null/partial when required labels are absent; this is not a benchmark claim."}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
