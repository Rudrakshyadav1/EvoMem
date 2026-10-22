"""Rebuildable local index. Hash vectors are deterministic test baselines, not semantic embeddings."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .repository import MemoryRepository
from .providers import EmbeddingProvider, LocalHashEmbedder
from .retrieval import serialize, tokens

INDEX_VERSION = "1.0"
MODEL_ID = "local-hash-token-v1"


def hash_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokens(text):
        vector[int(hashlib.sha256(token.encode()).hexdigest(), 16) % dimensions] += 1.0
    return vector


def rebuild(store: str | Path, output: str | Path, embedder: EmbeddingProvider | None = None) -> dict:
    embedder = embedder or LocalHashEmbedder()
    records = MemoryRepository(store).list()
    items = []
    for memory in records:
        text = serialize(memory); vector = embedder.embed(text)
        if not vector: raise ValueError("Embedding provider returned an empty vector.")
        items.append({"memory_id": memory.memory_id, "status": memory.status, "text": text, "embedding": vector})
    payload = {"index_version": INDEX_VERSION, "embedding_provider": embedder.provider, "embedding_model": embedder.model, "dimensions": len(items[0]["embedding"]) if items else embedder.dimensions, "items": items}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def load(path: str | Path, *, expected_model: str = MODEL_ID, expected_dimensions: int = 64) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("embedding_model") != expected_model or value.get("dimensions") != expected_dimensions:
        raise ValueError("Incompatible index model or vector dimension; rebuild the index.")
    return value
