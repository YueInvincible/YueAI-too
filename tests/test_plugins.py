import json
import unittest
from pathlib import Path

from yue_core.events import EventBus
from yue_core.plugins import PluginManager
from yue_core.providers import ModelProviderRegistry
from yue_core.services import ServiceRegistry
from yue_core.tools import ToolRegistry
from tests.support import workspace_temp_dir


PLUGIN_SOURCE = """
from yue_core.contracts import (
    Capability, ModelEvent, ModelEventType, RiskLevel, ToolSpec
)

class DemoTool:
    spec = ToolSpec(
        name="demo.plugin.ping",
        description="ping",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
        plugin_id="demo.plugin",
    )
    async def invoke(self, arguments, context):
        return {"pong": True}

class DemoPlugin:
    async def setup(self, context):
        context.register_tool(DemoTool())
        context.register_model_provider(DemoProvider())
    async def start(self):
        return None
    async def stop(self):
        return None

class DemoProvider:
    name = "demo.provider"
    async def generate(self, request, context):
        yield ModelEvent(ModelEventType.TEXT_DELTA, text="demo")
        yield ModelEvent(ModelEventType.FINISH, finish_reason="stop")
"""


class PluginTests(unittest.IsolatedAsyncioTestCase):
    async def test_load_start_and_stop_plugin(self):
        with workspace_temp_dir() as root:
            plugin_dir = root / "demo"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text(
                json.dumps(
                    {
                        "id": "demo.plugin",
                        "version": "0.1.0",
                        "core_api": "1.0",
                        "entrypoint": "plugin.py:DemoPlugin",
                    }
                ),
                encoding="utf-8",
            )
            (plugin_dir / "plugin.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
            registry = ToolRegistry()
            manager = PluginManager(
                [root],
                ["demo.plugin"],
                registry,
                EventBus(),
                ServiceRegistry(),
                ModelProviderRegistry(),
                {},
            )

            await manager.load_enabled()
            await manager.start_all()
            self.assertEqual(registry.get("demo.plugin.ping").spec.plugin_id, "demo.plugin")
            self.assertEqual(manager.providers.get("demo.provider").name, "demo.provider")
            await manager.stop_all()
            with self.assertRaises(KeyError):
                registry.get("demo.plugin.ping")
            with self.assertRaises(KeyError):
                manager.providers.get("demo.provider")


if __name__ == "__main__":
    unittest.main()
