import unittest
import asyncio

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings
from yue_core.contracts import ModelEvent, ModelEventType


class BlockingProvider:
    name = "test.shutdown"

    async def generate(self, request, context):
        await asyncio.sleep(60)
        yield ModelEvent(ModelEventType.FINISH)


class AppLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_core_can_restart_cleanly(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            await core.stop()
            await core.start()
            result = await core.invoke("core.health", {})
            await core.stop()
        self.assertTrue(result.ok)

    async def test_stop_cancels_active_conversation(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            core.providers.register(BlockingProvider(), owner="test")
            conversation = await core.conversations.create()
            started = asyncio.Event()

            async def mark_started(event):
                if event.payload["run_id"] == "shutdown-run":
                    started.set()

            unsubscribe = core.events.subscribe(
                "conversation.run.started", mark_started
            )
            task = asyncio.create_task(
                core.conversations.send(
                    conversation.id,
                    "wait",
                    provider_name="test.shutdown",
                    run_id="shutdown-run",
                )
            )
            await asyncio.wait_for(started.wait(), timeout=1)
            await core.stop()
            self.assertTrue(task.cancelled())
            unsubscribe()


if __name__ == "__main__":
    unittest.main()
