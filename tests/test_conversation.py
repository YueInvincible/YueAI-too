import asyncio
import unittest

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings
from yue_core.contracts import (
    MessageRole,
    ModelEvent,
    ModelEventType,
    ModelToolCall,
)
from yue_core.conversation import (
    ConversationError,
    InMemoryConversationStore,
    SQLiteConversationStore,
)


class ToolLoopProvider:
    name = "test.tool-loop"

    async def generate(self, request, context):
        tool_messages = [
            message for message in request.messages if message.role is MessageRole.TOOL
        ]
        if not tool_messages:
            yield ModelEvent(
                ModelEventType.TOOL_CALL,
                tool_call=ModelToolCall("core.echo", {"text": "from tool"}),
            )
            yield ModelEvent(ModelEventType.FINISH, finish_reason="tool_calls")
            return
        yield ModelEvent(ModelEventType.TEXT_DELTA, text="Tool said: ")
        yield ModelEvent(
            ModelEventType.TEXT_DELTA,
            text=tool_messages[-1].content,
        )
        yield ModelEvent(ModelEventType.FINISH, finish_reason="stop")


class EndlessToolProvider:
    name = "test.endless-tools"

    async def generate(self, request, context):
        yield ModelEvent(
            ModelEventType.TOOL_CALL,
            tool_call=ModelToolCall("core.echo", {"text": "again"}),
        )


class BlockingProvider:
    name = "test.blocking"

    async def generate(self, request, context):
        await asyncio.sleep(60)
        yield ModelEvent(ModelEventType.TEXT_DELTA, text="too late")


class RecordingProvider:
    name = "test.recording"

    def __init__(self) -> None:
        self.requests = []

    async def generate(self, request, context):
        self.requests.append(request)
        yield ModelEvent(ModelEventType.TEXT_DELTA, text="recorded")
        yield ModelEvent(ModelEventType.FINISH, finish_reason="stop")


class ConversationStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_preserves_order(self):
        store = InMemoryConversationStore()
        conversation = await store.create(title="Test")
        from yue_core.contracts import ChatMessage

        first = ChatMessage(conversation.id, MessageRole.USER, "one")
        second = ChatMessage(conversation.id, MessageRole.ASSISTANT, "two")
        await store.append(first)
        await store.append(second)
        self.assertEqual(await store.messages(conversation.id), (first, second))

    async def test_sqlite_store_persists_across_instances(self):
        with workspace_temp_dir() as temp:
            path = temp / "conversations.db"
            first_store = SQLiteConversationStore(path)
            conversation = await first_store.create(title="Persistent")
            from yue_core.contracts import ChatMessage

            message = ChatMessage(conversation.id, MessageRole.USER, "remember me")
            await first_store.append(message)

            second_store = SQLiteConversationStore(path)
            restored = await second_store.get(conversation.id)
            restored_messages = await second_store.messages(conversation.id)

        self.assertEqual(restored.title, "Persistent")
        self.assertEqual(restored_messages[0].content, "remember me")


class ConversationOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_context = workspace_temp_dir()
        temp = self.temp_context.__enter__()
        settings = Settings()
        settings.core.data_dir = temp
        self.core = YueCore(settings)
        await self.core.start()

    async def asyncTearDown(self):
        await self.core.stop()
        self.temp_context.__exit__(None, None, None)

    async def test_echo_provider_streams_and_persists(self):
        conversation = await self.core.conversations.create()
        deltas = []

        async def collect(event):
            deltas.append(event.payload["text"])

        unsubscribe = self.core.events.subscribe("conversation.delta", collect)
        assistant = await self.core.conversations.send(
            conversation.id,
            "hello",
            run_id="echo-run",
        )
        unsubscribe()
        messages = await self.core.conversation_store.messages(conversation.id)

        self.assertEqual(assistant.content, "Echo: hello")
        self.assertEqual("".join(deltas), "Echo: hello")
        self.assertEqual(
            [message.role for message in messages],
            [MessageRole.USER, MessageRole.ASSISTANT],
        )

    async def test_tool_loop_feeds_bounded_result_back(self):
        self.core.providers.register(ToolLoopProvider(), owner="test")
        conversation = await self.core.conversations.create()
        assistant = await self.core.conversations.send(
            conversation.id,
            "use a tool",
            provider_name="test.tool-loop",
        )
        messages = await self.core.conversation_store.messages(conversation.id)

        self.assertIn('"text": "from tool"', assistant.content)
        self.assertEqual(
            [message.role for message in messages],
            [
                MessageRole.USER,
                MessageRole.ASSISTANT,
                MessageRole.TOOL,
                MessageRole.ASSISTANT,
            ],
        )

    async def test_tool_iteration_limit(self):
        self.core.providers.register(EndlessToolProvider(), owner="test")
        self.core.conversations.max_tool_iterations = 1
        conversation = await self.core.conversations.create()
        with self.assertRaises(ConversationError):
            await self.core.conversations.send(
                conversation.id,
                "loop",
                provider_name="test.endless-tools",
            )

    async def test_cancel_interrupts_provider(self):
        self.core.providers.register(BlockingProvider(), owner="test")
        conversation = await self.core.conversations.create()
        started = asyncio.Event()

        async def mark_started(event):
            if event.payload["run_id"] == "cancel-me":
                started.set()

        unsubscribe = self.core.events.subscribe(
            "conversation.run.started", mark_started
        )
        task = asyncio.create_task(
            self.core.conversations.send(
                conversation.id,
                "wait",
                provider_name="test.blocking",
                run_id="cancel-me",
            )
        )
        await asyncio.wait_for(started.wait(), timeout=1)
        self.assertTrue(self.core.conversations.cancel("cancel-me"))
        with self.assertRaises(asyncio.CancelledError):
            await task
        unsubscribe()

    async def test_same_conversation_runs_are_serialized(self):
        conversation = await self.core.conversations.create()
        first = asyncio.create_task(
            self.core.conversations.send(conversation.id, "one", run_id="one")
        )
        second = asyncio.create_task(
            self.core.conversations.send(conversation.id, "two", run_id="two")
        )
        await asyncio.gather(first, second)
        messages = await self.core.conversation_store.messages(conversation.id)
        self.assertEqual(
            [message.content for message in messages],
            ["one", "Echo: one", "two", "Echo: two"],
        )

    async def test_provider_role_uses_route_and_prompt_profile(self):
        provider = RecordingProvider()
        self.core.providers.register(provider, owner="test")
        self.core.conversations.routes["coding_agent"] = {
            "provider": "test.recording",
            "prompt_profile": "coding",
        }
        self.core.conversations.prompt_profiles["coding"] = {
            "personality": "Direct and technical.",
            "system_instruction": "You are the coding agent.",
            "tool_instruction": "Use tools precisely.",
            "response_instruction": "Return concise answers.",
        }
        conversation = await self.core.conversations.create()

        assistant = await self.core.conversations.send(
            conversation.id,
            "build it",
            provider_role="coding_agent",
        )

        request = provider.requests[-1]
        self.assertEqual(request.messages[0].role, MessageRole.SYSTEM)
        self.assertIn("You are the coding agent.", request.messages[0].content)
        self.assertEqual(assistant.metadata["provider_role"], "coding_agent")
        self.assertEqual(assistant.metadata["prompt_profile"], "coding")


if __name__ == "__main__":
    unittest.main()
