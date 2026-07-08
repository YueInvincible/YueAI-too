from __future__ import annotations

import json
from typing import Any


AGENT_STARTER_PACK_FORMATS: tuple[str, ...] = (
    "text",
    "json",
    "manifest-json",
    "system-prompt",
    "starter-prompt",
    "checklist",
)


def render_agent_starter_pack_output(payload: dict[str, Any], format_name: str) -> str:
    if format_name == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if format_name == "text":
        return str(payload["text"])
    if format_name == "manifest-json":
        return str(payload["tool_manifest_json"])
    if format_name == "system-prompt":
        return str(payload["system_prompt"])
    if format_name == "starter-prompt":
        return str(payload["starter_prompt"])
    if format_name == "checklist":
        items = payload.get("integration_checklist", [])
        return "\n".join(f"- {item}" for item in items)
    raise ValueError(f"Unsupported export format: {format_name}")
