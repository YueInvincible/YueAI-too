from __future__ import annotations

import asyncio

from .contracts import (
    MessageRole,
    ModelContext,
    ModelEvent,
    ModelEventType,
    ModelRequest,
)


class EchoModelProvider:
    """Deterministic provider used for core development and transport tests."""

    name = "fake.echo"

    def __init__(self, *, chunk_size: int = 8) -> None:
        self.chunk_size = max(1, chunk_size)

    async def generate(self, request: ModelRequest, context: ModelContext):
        last_user = next(
            (
                message.content
                for message in reversed(request.messages)
                if message.role is MessageRole.USER
            ),
            "",
        )
        response = f"Echo: {last_user}"
        for index in range(0, len(response), self.chunk_size):
            if context.cancelled():
                return
            await asyncio.sleep(0)
            yield ModelEvent(
                ModelEventType.TEXT_DELTA,
                text=response[index : index + self.chunk_size],
            )
        yield ModelEvent(ModelEventType.FINISH, finish_reason="stop")

    async def health(self):
        return {
            "provider": self.name,
            "ok": True,
            "backend": "fake",
            "reachable": True,
        }

