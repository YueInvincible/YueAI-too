import unittest
from pathlib import Path

from yue_core.audit import AuditLog
from yue_core.builtin_tools import EchoTool
from yue_core.contracts import (
    Capability,
    RiskLevel,
    ToolRequest,
    ToolSpec,
    ToolStatus,
)
from yue_core.events import EventBus
from yue_core.permissions import PermissionEngine
from yue_core.tools import ToolExecutor, ToolRegistry
from tests.support import workspace_temp_dir


class ToolExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_context = workspace_temp_dir()
        self.temp = self.temp_context.__enter__()
        registry = ToolRegistry()
        registry.register(EchoTool())
        self.executor = ToolExecutor(
            registry,
            PermissionEngine("observe"),
            EventBus(),
            AuditLog(self.temp / "audit.jsonl"),
        )

    async def asyncTearDown(self):
        self.temp_context.__exit__(None, None, None)

    async def test_executes_valid_tool(self):
        result = await self.executor.execute(
            ToolRequest("core.echo", {"text": "hello"})
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(result.output, {"text": "hello"})

    async def test_rejects_invalid_arguments(self):
        result = await self.executor.execute(
            ToolRequest("core.echo", {"wrong": "hello"})
        )
        self.assertEqual(result.status, ToolStatus.FAILED)

    async def test_unknown_tool_is_audited_and_failed(self):
        result = await self.executor.execute(ToolRequest("missing.tool", {}))
        self.assertEqual(result.status, ToolStatus.FAILED)
        audit_text = (self.temp / "audit.jsonl").read_text(encoding="utf-8")
        self.assertIn("tool.request", audit_text)
        self.assertIn("tool.result", audit_text)

    async def test_timeout(self):
        class SlowTool:
            spec = ToolSpec(
                "test.slow",
                "slow",
                {"type": "object", "properties": {}, "additionalProperties": False},
                Capability.CORE_READ,
                RiskLevel.LOW,
                timeout_seconds=0.01,
            )

            async def invoke(self, arguments, context):
                import asyncio

                await asyncio.sleep(1)

        self.executor.registry.register(SlowTool())
        result = await self.executor.execute(ToolRequest("test.slow", {}))
        self.assertEqual(result.status, ToolStatus.TIMED_OUT)


if __name__ == "__main__":
    unittest.main()
