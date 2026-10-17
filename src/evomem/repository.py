from __future__ import annotations

import json
from pathlib import Path

from .schemas import Memory, memory_from_dict, now


class MemoryRepository:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, memory: Memory) -> Path:
        memory.updated_at = now()
        path = self.root / f"{memory.memory_id}.json"
        path.write_text(json.dumps(memory.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def get(self, memory_id: str) -> Memory:
        return memory_from_dict(json.loads((self.root / f"{memory_id}.json").read_text(encoding="utf-8")))

    def list(self, trusted_only: bool = False) -> list[Memory]:
        records = [memory_from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in sorted(self.root.glob("*.json"))]
        return [record for record in records if record.status == "validated"] if trusted_only else records
