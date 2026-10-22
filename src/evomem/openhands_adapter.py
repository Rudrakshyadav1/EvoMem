"""OpenHands boundary: serializable requests now, direct SDK only when healthy."""
from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from typing import Any

from .evaluation_runner import EvaluationPlanItem


@dataclass(frozen=True)
class AdapterHealth:
    available: bool
    reason: str


@dataclass(frozen=True)
class OpenHandsRunRequest:
    task_id: str
    condition: str
    repository: str
    task_prompt: str
    agent_context: dict[str, Any]
    budget: dict[str, Any]


def health() -> AdapterHealth:
    try:
        sdk = importlib.import_module("openhands.sdk")
        required = ("LLM", "Agent", "Conversation")
        missing = [name for name in required if not hasattr(sdk, name)]
        if missing:
            return AdapterHealth(False, "OpenHands SDK is missing required symbols: " + ", ".join(missing))
    except Exception as exc:
        return AdapterHealth(False, f"OpenHands SDK import failed: {type(exc).__name__}: {str(exc).splitlines()[0]}")
    return AdapterHealth(True, "OpenHands SDK import is available; configure an agent runner before executing tasks.")


def build_request(item: EvaluationPlanItem, task_prompt: str, agent_context: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    """Build, but do not execute, a request for an external OpenHands runner."""
    context = {**agent_context}
    if item.condition == "no_memory":
        context["accepted_memories"] = []
        context["abstained"] = True
    return asdict(OpenHandsRunRequest(item.task_id, item.condition, item.repository, task_prompt, context, budget))
