from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    semantic_weight: float = .45
    lexical_weight: float = .35
    language_weight: float = .10
    validation_weight: float = .10
    top_k: int = 5
    gate_minimum_score: float = .35
    allow_partially_validated: bool = False

    def validate(self) -> "Settings":
        if min(self.semantic_weight, self.lexical_weight, self.language_weight, self.validation_weight) < 0:
            raise ValueError("Retrieval weights must be non-negative.")
        if round(self.semantic_weight + self.lexical_weight + self.language_weight + self.validation_weight, 8) != 1:
            raise ValueError("Retrieval weights must sum to 1.")
        if not 0 <= self.gate_minimum_score <= 1:
            raise ValueError("Gate threshold must be within [0, 1].")
        return self


def load_settings(path: str | Path = "configs/default.json") -> Settings:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    retrieval, policy = raw.get("retrieval", {}), raw.get("gate", {})
    return Settings(retrieval.get("semantic_weight", .45), retrieval.get("lexical_weight", .35), retrieval.get("language_weight", .1),
                    retrieval.get("validation_weight", .1), retrieval.get("top_k", 5), policy.get("minimum_score", .35),
                    policy.get("allow_partially_validated", False)).validate()
