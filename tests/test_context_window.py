import unittest

from yue_core.context_window import ContextWindowPolicy
from yue_core.contracts import ChatMessage, MessageRole, ModelToolCall, ToolSpec


class ContextWindowPolicyTests(unittest.TestCase):
    def test_keeps_complete_recent_turns_with_bounded_message_content(self):
        conversation_id = "conversation-1"
        history = []
        for index in range(4):
            history.extend(
                [
                    ChatMessage(
                        conversation_id=conversation_id,
                        role=MessageRole.USER,
                        content=f"user-{index}-" + ("u" * 200),
                    ),
                    ChatMessage(
                        conversation_id=conversation_id,
                        role=MessageRole.ASSISTANT,
                        content=f"assistant-{index}-" + ("a" * 200),
                    ),
                ]
            )

        bounded = ContextWindowPolicy(
            max_history_messages=4,
            max_history_chars=600,
            max_message_chars=150,
            max_system_instruction_chars=256,
        ).bound_history(history)

        self.assertEqual(len(bounded), 4)
        self.assertTrue(bounded[0].content.startswith("user-2-"))
        self.assertTrue(bounded[2].content.startswith("user-3-"))
        self.assertTrue(all(len(message.content) <= 150 for message in bounded))
        self.assertLessEqual(sum(len(message.content) for message in bounded), 600)

    def test_summarizes_oversized_historical_tool_arguments(self):
        message = ChatMessage(
            conversation_id="conversation-1",
            role=MessageRole.ASSISTANT,
            tool_calls=(
                ModelToolCall(
                    id="call-1",
                    name="workspace_write",
                    arguments={"content": "x" * 5000},
                ),
            ),
        )
        bounded = ContextWindowPolicy(
            max_history_messages=4,
            max_history_chars=1024,
            max_message_chars=256,
            max_system_instruction_chars=256,
        ).bound_history((message,))

        arguments = bounded[0].tool_calls[0].arguments
        self.assertTrue(arguments["_context_truncated"])
        self.assertGreater(arguments["original_chars"], 5000)

    def test_pathological_latest_tool_exchange_falls_back_to_valid_user_anchor(self):
        conversation_id = "conversation-1"
        history = [
            ChatMessage(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content="do the work",
            ),
            ChatMessage(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                tool_calls=tuple(
                    ModelToolCall(name="workspace_read", arguments={"path": str(index)})
                    for index in range(8)
                ),
            ),
            *[
                ChatMessage(
                    conversation_id=conversation_id,
                    role=MessageRole.TOOL,
                    content="result",
                    tool_call_id=f"call-{index}",
                )
                for index in range(8)
            ],
        ]
        bounded = ContextWindowPolicy(
            max_history_messages=4,
            max_history_chars=1024,
            max_message_chars=256,
        ).bound_history(history)

        self.assertEqual(len(bounded), 1)
        self.assertEqual(bounded[0].role, MessageRole.USER)
        self.assertEqual(bounded[0].content, "do the work")

    def test_bounds_system_instruction_head_and_tail(self):
        policy = ContextWindowPolicy(max_system_instruction_chars=256)
        bounded = policy.bound_system_instruction("head" + ("x" * 500) + "tail")

        self.assertEqual(len(bounded), 256)
        self.assertTrue(bounded.startswith("head"))
        self.assertTrue(bounded.endswith("tail"))
        self.assertIn("context truncated", bounded)

    def test_bounds_tool_count_and_rejects_oversized_specs(self):
        tools = (
            ToolSpec("small.one", "small", {"type": "object"}),
            ToolSpec("too.large", "x" * 500, {"type": "object"}),
            ToolSpec("small.two", "small", {"type": "object"}),
        )
        bounded = ContextWindowPolicy(
            max_model_tools=1,
            max_tool_spec_chars=256,
            max_tool_catalog_chars=256,
        ).bound_tools(tools)

        self.assertEqual([tool.name for tool in bounded], ["small.one"])


if __name__ == "__main__":
    unittest.main()
