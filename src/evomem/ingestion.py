from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import NormalizedEvent, NormalizedTrajectory


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _message_text(event: dict[str, Any]) -> str:
    content = event.get("llm_message", {}).get("content", event.get("content", []))
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
    return _text(content)


def normalize(path: str | Path) -> NormalizedTrajectory:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed trajectory JSON: {exc.msg}") from exc
    if isinstance(raw, dict):
        raw = raw.get("events", raw.get("trajectory", []))
    if not isinstance(raw, list):
        raise ValueError("Trajectory must be an event list or an object containing events")
    events: list[NormalizedEvent] = []
    warnings: list[str] = []
    task = None
    for sequence, event in enumerate(raw):
        if not isinstance(event, dict):
            warnings.append(f"Skipped non-object event at index {sequence}")
            continue
        kind = str(event.get("kind", event.get("type", "UnknownEvent")))
        if kind == "MessageEvent":
            text = _message_text(event)
            if task is None and text.strip():
                task = text.strip()
        elif kind == "ActionEvent":
            text = _text(event.get("action", event.get("summary", "")))
        elif kind == "ObservationEvent":
            text = _text(event.get("observation", ""))
        else:
            text = _text(event.get("text", event.get("message", "")))
        events.append(NormalizedEvent(str(event.get("id", f"event-{sequence}")), sequence, kind,
                                      event.get("timestamp"), event.get("tool_name"), text, event))
    if not events:
        warnings.append("Trajectory contains no usable events")
    return NormalizedTrajectory(str(source), task, events, warnings)
