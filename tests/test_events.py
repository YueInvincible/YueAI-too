import asyncio
import unittest

from yue_core.contracts import CoreEvent
from yue_core.events import EventBus


class EventBusTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_wildcard_and_global_subscribers(self):
        bus = EventBus()
        received = []

        async def collect(event):
            received.append(event.topic)

        bus.subscribe("tool.started", collect)
        bus.subscribe("tool.*", collect)
        bus.subscribe("*", collect)

        await bus.publish(CoreEvent("tool.started"))

        self.assertEqual(received, ["tool.started", "tool.started", "tool.started"])

    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        async def collect(event):
            received.append(event.topic)

        unsubscribe = bus.subscribe("core.started", collect)
        unsubscribe()
        await bus.publish(CoreEvent("core.started"))
        self.assertEqual(received, [])


if __name__ == "__main__":
    unittest.main()

