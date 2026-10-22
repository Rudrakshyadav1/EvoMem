"""Provider boundary. Cloud calls remain optional and are never used in tests."""
from __future__ import annotations

from typing import Protocol


class StructuredLLM(Protocol):
    provider: str
    model: str
    def generate_json(self, prompt: str, schema: dict) -> dict: ...


class UnavailableProvider:
    def __init__(self, provider: str = "none", model: str = "none"):
        self.provider, self.model = provider, model

    def generate_json(self, prompt: str, schema: dict) -> dict:
        raise RuntimeError("No LLM provider is configured. Use deterministic_distill for offline processing.")


def provider_metadata(client: StructuredLLM) -> dict[str, str]:
    return {"provider": client.provider, "model": client.model}
