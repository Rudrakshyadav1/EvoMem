from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Status = Literal["candidate", "partially_validated", "validated", "rejected", "stale", "quarantined"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvidenceRef:
    event_id: str
    field: str
    excerpt: str
    evidence_type: Literal["trajectory", "repository", "execution"] = "trajectory"


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    sequence: int
    kind: str
    timestamp: str | None
    tool_name: str | None
    text: str
    source: dict[str, Any]


@dataclass
class NormalizedTrajectory:
    source_path: str
    task: str | None
    events: list[NormalizedEvent]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "1.0", "source_path": self.source_path, "task": self.task,
                "events": [asdict(e) for e in self.events], "warnings": self.warnings}


@dataclass
class Claim:
    claim_id: str
    text: str
    category: Literal["language", "command", "file", "test", "solution", "lesson", "failure", "recovery"]
    evidence: list[EvidenceRef]
    origin: Literal["observed", "inferred", "llm"]
    result: Literal["pending", "verified", "unsupported", "uncertain"] = "pending"
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = [asdict(e) for e in self.evidence]
        return data


@dataclass
class Memory:
    memory_id: str
    task: dict[str, Any]
    solution: dict[str, Any]
    claims: list[Claim]
    provenance: dict[str, Any]
    context: dict[str, Any]
    status: Status = "candidate"
    validation: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["claims"] = [claim.to_dict() for claim in self.claims]
        return data


def memory_from_dict(data: dict[str, Any]) -> Memory:
    required = {"memory_id", "task", "solution", "claims", "provenance", "context", "status"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Memory is missing required fields: {', '.join(sorted(missing))}")
    status = data["status"]
    if status not in {"candidate", "partially_validated", "validated", "rejected", "stale", "quarantined"}:
        raise ValueError(f"Invalid lifecycle status: {status}")
    claims = []
    for raw in data["claims"]:
        refs = [EvidenceRef(**ref) for ref in raw.get("evidence", [])]
        claims.append(Claim(**{**raw, "evidence": refs}))
    return Memory(memory_id=data["memory_id"], task=data["task"], solution=data["solution"], claims=claims,
                  provenance=data["provenance"], context=data["context"], status=status,
                  validation=data.get("validation", {}), created_at=data.get("created_at", now()),
                  updated_at=data.get("updated_at", now()), schema_version=data.get("schema_version", "1.0"))
