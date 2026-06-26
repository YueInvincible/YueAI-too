from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import Capability, RiskLevel, ToolContext, ToolSpec


class EchoTool:
    spec = ToolSpec(
        name="core.echo",
        description="Return text unchanged. Used for health checks and integration tests.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "maxLength": 10000}},
            "required": ["text"],
            "additionalProperties": False,
        },
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        return {"text": arguments["text"]}


class HealthTool:
    spec = ToolSpec(
        name="core.health",
        description="Return a minimal health snapshot for the running core.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        return {
            "status": "ok",
            "request_id": context.request.id,
            "services": sorted(context.services),
        }

