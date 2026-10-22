from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .schemas import Memory
from .security import safe_relative_path, safety_warnings

FORBIDDEN_COMMAND_TOKENS = ("rm -rf", "curl ", "wget ", "nc ", "ssh ", "sudo ", "chmod 777")


def validate(memory: Memory, snapshot_root: str | Path | None = None) -> Memory:
    root = Path(snapshot_root).resolve() if snapshot_root else None
    verified = unsupported = uncertain = 0
    updated = []
    for claim in memory.claims:
        result, reason = "verified", None
        if not claim.evidence:
            result, reason = "unsupported", "No source evidence was attached."
        elif claim.origin == "llm" and claim.category in {"solution", "lesson", "recovery"}:
            result, reason = "uncertain", "LLM interpretation requires semantic or execution evidence beyond cited text."
        elif claim.category == "file" and root:
            name = claim.text.removeprefix("Referenced file: ")
            if not safe_relative_path(name):
                result, reason = "unsupported", "File reference is not a safe relative path."
                updated.append(replace(claim, result=result, reason=reason)); unsupported += 1; continue
            candidate = (root / name).resolve()
            if root not in candidate.parents and candidate != root:
                result, reason = "unsupported", "File reference escapes the snapshot root."
            elif not candidate.exists():
                result, reason = "unsupported", "Referenced file does not exist in snapshot."
        elif claim.category == "command":
            lowered = claim.text.lower()
            if any(token in lowered for token in FORBIDDEN_COMMAND_TOKENS):
                result, reason = "uncertain", "Potentially unsafe command; execution validation was skipped."
        if safety_warnings(claim.text):
            result, reason = "uncertain", "Untrusted instruction-like content; claim is quarantined from automated use."
        updated.append(replace(claim, result=result, reason=reason))
        if result == "verified": verified += 1
        elif result == "unsupported": unsupported += 1
        else: uncertain += 1
    status = "quarantined" if any(safety_warnings(c.text) for c in updated) else "validated" if updated and not unsupported and not uncertain else "partially_validated" if verified else "rejected"
    validation = {"schema": "verified", "execution": {"status": "skipped", "reason": "No isolated executor configured."},
                  "summary": {"verified": verified, "unsupported": unsupported, "uncertain": uncertain}}
    return replace(memory, claims=updated, status=status, validation=validation)
