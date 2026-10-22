"""Read-only repository fingerprints for compatibility checks, not code analysis."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

MANIFESTS = ("pyproject.toml", "requirements.txt", "package.json", "package-lock.json", "poetry.lock", "Cargo.toml", "go.mod", "pom.xml", "build.gradle")


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _safe_remote(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme and parsed.hostname:
        return urlunsplit((parsed.scheme, parsed.hostname, parsed.path, "", ""))
    return value.split("@")[-1]


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect(root: str | Path, *, files: list[str] | None = None, max_file_bytes: int = 2_000_000) -> dict:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"Repository root does not exist or is not a directory: {root_path}")
    selected = files or [name for name in MANIFESTS if (root_path / name).is_file()]
    hashes: dict[str, str] = {}
    skipped: list[str] = []
    for name in selected:
        candidate = (root_path / name).resolve()
        if root_path not in candidate.parents or not candidate.is_file() or candidate.stat().st_size > max_file_bytes:
            skipped.append(name); continue
        hashes[str(candidate.relative_to(root_path))] = _hash(candidate)
    remote = _safe_remote(_git(root_path, "config", "--get", "remote.origin.url"))
    commit = _git(root_path, "rev-parse", "HEAD")
    return {"repository": remote or str(root_path.name), "commit": commit, "dependencies": {}, "file_hashes": hashes,
            "fingerprint_scope": "explicit files or dependency manifests only", "skipped_files": skipped}
