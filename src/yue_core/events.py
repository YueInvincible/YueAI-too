from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator, Callable

from .contracts import CoreEvent, EventHandler

LOGGER = logging.getLogger(__name__)


class EventBus:
    """In-process async event bus with exact and namespace-wildcard topics."""

    def __init__(self) -> None:
        self._handlers: dict[str, dict[int, EventHandler]] = defaultdict(dict)
        self._next_token = 0
        self._lock = asyncio.Lock()

    async def publish(self, event: CoreEvent) -> None:
        handlers = await self._matching_handlers(event.topic)
        if not handlers:
            return
        results = await asyncio.gather(
            *(handler(event) for handler in handlers),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException):
                LOGGER.exception(
                    "Event handler failed for topic %s",
                    event.topic,
                    exc_info=result,
                )

    def subscribe(self, topic: str, handler: EventHandler) -> Callable[[], None]:
        if not topic or (
            topic != "*" and "*" in topic and not topic.endswith(".*")
        ):
            raise ValueError("Topic must be exact or end with .*")
        token = self._next_token
        self._next_token += 1
        self._handlers[topic][token] = handler

        def unsubscribe() -> None:
            handlers = self._handlers.get(topic)
            if handlers is not None:
                handlers.pop(token, None)
                if not handlers:
                    self._handlers.pop(topic, None)

        return unsubscribe

    async def stream(
        self,
        topic: str = "*",
        *,
        max_queue_size: int = 256,
    ) -> AsyncIterator[CoreEvent]:
        queue: asyncio.Queue[CoreEvent] = asyncio.Queue(maxsize=max_queue_size)

        async def enqueue(event: CoreEvent) -> None:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                LOGGER.warning("Dropping event from full stream queue: %s", event.topic)

        subscription = "*" if topic == "*" else topic
        unsubscribe = self.subscribe(subscription, enqueue)
        try:
            while True:
                yield await queue.get()
        finally:
            unsubscribe()

    async def _matching_handlers(self, topic: str) -> list[EventHandler]:
        async with self._lock:
            handlers = list(self._handlers.get(topic, {}).values())
            handlers.extend(self._handlers.get("*", {}).values())
            parts = topic.split(".")
            for index in range(1, len(parts)):
                wildcard = ".".join(parts[:index]) + ".*"
                handlers.extend(self._handlers.get(wildcard, {}).values())
            return handlers
