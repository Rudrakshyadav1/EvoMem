from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Compatibility:
    state: str
    reasons: list[str]


def compare_context(memory_context: dict[str, Any], current: dict[str, Any]) -> Compatibility:
    """Targeted compatibility, avoiding 'any commit change means stale'."""
    reasons: list[str] = []
    old_repo, new_repo = memory_context.get("repository"), current.get("repository")
    if old_repo and new_repo and old_repo != new_repo:
        return Compatibility("incompatible", ["Repository identifiers differ."])
    old_deps, new_deps = memory_context.get("dependencies", {}), current.get("dependencies", {})
    if isinstance(old_deps, list): old_deps = {}
    if isinstance(new_deps, list): new_deps = {}
    changed = [name for name, version in old_deps.items() if name in new_deps and new_deps[name] != version]
    if changed:
        reasons.append("Dependency versions changed: " + ", ".join(sorted(changed)))
    old_hashes, new_hashes = memory_context.get("file_hashes", {}), current.get("file_hashes", {})
    touched = [name for name, value in old_hashes.items() if name in new_hashes and new_hashes[name] != value]
    if touched:
        reasons.append("Relevant files changed: " + ", ".join(sorted(touched)))
    if reasons:
        return Compatibility("warning", reasons)
    if not old_repo or not new_repo:
        return Compatibility("unknown", ["Insufficient repository context for drift determination."])
    return Compatibility("compatible", ["Repository and tracked dependency/file fingerprints are compatible."])
