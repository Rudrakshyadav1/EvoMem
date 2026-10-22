"""Treat trajectories and memories as data, never as instructions."""
from __future__ import annotations

import re

INJECTION_PATTERNS = (
    r"ignore (all |previous |prior )?instructions",
    r"reveal .*?(secret|api.?key|token|password)",
    r"system prompt",
    r"exfiltrat",
)


def safety_warnings(text: str) -> list[str]:
    return [f"Untrusted-content pattern: {pattern}" for pattern in INJECTION_PATTERNS if re.search(pattern, text, re.I)]


def safe_relative_path(path: str) -> bool:
    return bool(path) and not path.startswith(("/", "\\")) and ".." not in path.replace("\\", "/").split("/")
