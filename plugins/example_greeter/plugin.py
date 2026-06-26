from collections.abc import Mapping
from typing import Any

from yue_core.contracts import (
    Capability,
    CoreEvent,
    RiskLevel,
    ToolContext,
    ToolSpec,
)


class GreetingTool:
    spec = ToolSpec(
        name="example.greeter.greet",
        description="Create a simple greeting without side effects.",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 100}
            },
            "required": ["name"],
            "additionalProperties": False
        },
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
        plugin_id="example.greeter",
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        message = f"Hello, {arguments['name']}!"
        await context.publish(
            CoreEvent(
                "example.greeter.greeted",
                {"name": arguments["name"]},
                source="example.greeter",
                correlation_id=context.request.id,
            )
        )
        return {"message": message}


class GreeterPlugin:
    async def setup(self, context) -> None:
        self.context = context
        context.register_tool(GreetingTool())

    async def start(self) -> None:
        await self.context.publish(
            CoreEvent("plugin.ready", {"plugin_id": "example.greeter"})
        )

    async def stop(self) -> None:
        return None
