from __future__ import annotations

import hashlib
import re

from .schemas import Claim, EvidenceRef, Memory, NormalizedTrajectory


def _refs(trajectory: NormalizedTrajectory, predicate) -> list[EvidenceRef]:
    return [EvidenceRef(e.event_id, "text", e.text[:500]) for e in trajectory.events if predicate(e.text.lower())]


def deterministic_distill(trajectory: NormalizedTrajectory) -> Memory:
    task = trajectory.task or "Task unavailable in trajectory"
    joined = "\n".join(e.text for e in trajectory.events)
    language = "C++" if re.search(r"\bg\+\+|\.cpp\b|\bc\+\+", joined, re.I) else "Python" if re.search(r"\bpython\d*|\.py\b", joined, re.I) else "unknown"
    commands = [e for e in trajectory.events if e.kind == "ActionEvent" and any(x in e.text.lower() for x in ("command", "g++", "python", "pytest", "test"))]
    # Deliberately exclude compiler flags such as `c++17`; this is a conservative
    # filename extractor, not a source-of-truth file-operation parser.
    files = sorted(set(re.findall(r"(?<![\w+.-])(?:[\w.-]+/)*[\w.-]+\.(?:py|cpp|cc|cxx|java)\b", joined)))
    claims: list[Claim] = []
    if language != "unknown":
        refs = _refs(trajectory, lambda t: language.lower() in t or (language == "C++" and ("g++" in t or ".cpp" in t)))
        claims.append(Claim("language-1", f"The trajectory concerns {language}.", "language", refs, "inferred"))
    for index, command in enumerate(commands):
        claims.append(Claim(f"command-{index + 1}", command.text, "command", [EvidenceRef(command.event_id, "text", command.text[:500])], "observed"))
    for index, file_name in enumerate(files):
        refs = _refs(trajectory, lambda t, f=file_name.lower(): f in t)
        claims.append(Claim(f"file-{index + 1}", f"Referenced file: {file_name}", "file", refs, "observed"))
    errors = _refs(trajectory, lambda t: "error" in t or "failed" in t)
    for index, ref in enumerate(errors):
        claims.append(Claim(f"failure-{index + 1}", ref.excerpt, "failure", [ref], "observed"))
    stable = hashlib.sha256((task + "\n" + joined).encode()).hexdigest()[:16]
    return Memory(f"mem-{stable}", {"description": task, "language": language, "domain": "unknown"},
                  {"approach": "Not inferred without explicit evidence.", "key_ideas": [], "files": files}, claims,
                  {"trajectory_path": trajectory.source_path, "event_ids": [e.event_id for e in trajectory.events]},
                  {"repository": None, "commit": None, "dependencies": []})
