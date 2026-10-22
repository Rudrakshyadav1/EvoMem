"""Optional model providers. Tests use local deterministic implementations only."""
from __future__ import annotations

import json
import os
import time
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path


def _hash_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for token in set(re.findall(r"[a-z0-9_+#.-]+", text.lower())):
        vector[int(hashlib.sha256(token.encode()).hexdigest(), 16) % dimensions] += 1.0
    return vector


def _load_project_environment() -> None:
    """Load only missing variables from a local .env without logging its contents."""
    env_file = Path.cwd() / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


class ProviderError(RuntimeError):
    pass


class StructuredProvider(Protocol):
    provider: str
    model: str
    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]: ...


class EmbeddingProvider(Protocol):
    provider: str
    model: str
    dimensions: int
    def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class LocalHashEmbedder:
    provider: str = "local"
    model: str = "local-hash-token-v1"
    dimensions: int = 64
    def embed(self, text: str) -> list[float]:
        return _hash_embedding(text, self.dimensions)


class GeminiREST:
    """Minimal Gemini REST client with bounded retries; API keys never enter output."""
    provider = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, model: str, *, api_key: str | None = None, timeout_seconds: int = 45, retries: int = 3):
        self.model = model.removeprefix("models/")
        _load_project_environment()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.timeout_seconds, self.retries = timeout_seconds, retries
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY is required for the Gemini provider.")

    def _post(self, suffix: str, body: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(body).encode("utf-8")
        url = f"{self.base_url}/models/{self.model}:{suffix}"
        last_error: Exception | None = None
        for attempt in range(self.retries):
            request = Request(url, data=encoded, headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key}, method="POST")
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                last_error = exc
                if exc.code not in (429, 500, 502, 503, 504): break
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
            time.sleep(min(2 ** attempt, 4))
        status = f" HTTP {last_error.code}." if isinstance(last_error, HTTPError) else ""
        raise ProviderError(f"Gemini request failed after {self.retries} attempt(s): {type(last_error).__name__}.{status}") from last_error

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        raw = self._post("generateContent", {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema}})
        try:
            text = raw["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("Gemini returned no valid JSON candidate.") from exc

    def embed(self, text: str) -> list[float]:
        raw = self._post("embedContent", {"content": {"parts": [{"text": text}]}})
        try:
            return [float(value) for value in raw["embedding"]["values"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("Gemini returned no valid embedding vector.") from exc


def validate_json_shape(value: Any, schema: dict[str, Any]) -> None:
    """Small strict validator for the project-controlled response schemas."""
    if schema.get("type") == "object":
        if not isinstance(value, dict): raise ProviderError("Provider response must be a JSON object.")
        for field in schema.get("required", []):
            if field not in value: raise ProviderError(f"Provider response is missing required field: {field}")
        for field, child in schema.get("properties", {}).items():
            if field in value: validate_json_shape(value[field], child)
    elif schema.get("type") == "array":
        if not isinstance(value, list): raise ProviderError("Provider response has an invalid array field.")
        for item in value: validate_json_shape(item, schema.get("items", {}))
    elif schema.get("type") == "string" and not isinstance(value, str): raise ProviderError("Provider response has an invalid string field.")
