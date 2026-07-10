from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace

from .contracts import ChatMessage, MessageRole, ModelToolCall, ToolSpec


_TRUNCATION_MARKER = "\n...[context truncated]...\n"


@dataclass(frozen=True, slots=True)
class ContextWindowPolicy:
    """Deterministic character bounds applied before provider serialization."""

    max_history_messages: int = 64
    max_history_chars: int = 48000
    max_message_chars: int = 12000
    max_system_instruction_chars: int = 16000
    max_model_tools: int = 64
    max_tool_spec_chars: int = 8000
    max_tool_catalog_chars: int = 48000

    def bound_system_instruction(self, content: str) -> str:
        return _truncate_text(content, self.max_system_instruction_chars)

    def bound_tools(self, tools: Sequence[ToolSpec]) -> tuple[ToolSpec, ...]:
        selected: list[ToolSpec] = []
        used_chars = 0
        for spec in tools:
            spec_chars = len(spec.model_description()) + len(
                json.dumps(spec.input_schema, ensure_ascii=False, default=str)
            )
            if spec_chars > self.max_tool_spec_chars:
                continue
            if used_chars + spec_chars > self.max_tool_catalog_chars:
                continue
            selected.append(spec)
            used_chars += spec_chars
            if len(selected) >= self.max_model_tools:
                break
        return tuple(selected)

    def bound_history(self, history: Sequence[ChatMessage]) -> tuple[ChatMessage, ...]:
        if not history:
            return ()

        turns = _conversation_turns(history)
        selected: list[tuple[ChatMessage, ...]] = []
        remaining_messages = self.max_history_messages
        remaining_chars = self.max_history_chars

        for turn_index, turn in enumerate(reversed(turns)):
            if remaining_messages <= 0 or remaining_chars <= 0:
                break
            is_latest = turn_index == 0
            if is_latest:
                if len(turn) > remaining_messages:
                    # A partial tool exchange is invalid for provider APIs. In
                    # the pathological case, keep only the turn's user anchor
                    # and let the model reason again from a valid request.
                    turn = (turn[0],)
                per_message_limit = min(
                    self.max_message_chars,
                    max(1, remaining_chars // max(1, len(turn))),
                )
            else:
                if len(turn) > remaining_messages:
                    break
                per_message_limit = self.max_message_chars

            bounded = tuple(_bound_message(message, per_message_limit) for message in turn)
            turn_chars = sum(_message_context_chars(message) for message in bounded)
            if not is_latest and turn_chars > remaining_chars:
                break
            if is_latest and turn_chars > remaining_chars:
                overflow_per_message = (
                    turn_chars - remaining_chars + len(turn) - 1
                ) // len(turn)
                bounded = tuple(
                    _bound_message(message, max(1, per_message_limit - overflow_per_message))
                    for message in turn
                )
                turn_chars = sum(_message_context_chars(message) for message in bounded)
                if turn_chars > remaining_chars:
                    bounded = (_bound_message(turn[0], remaining_chars),)
                    turn_chars = _message_context_chars(bounded[0])

            selected.append(bounded)
            remaining_messages -= len(bounded)
            remaining_chars -= min(turn_chars, remaining_chars)

        return tuple(message for turn in reversed(selected) for message in turn)


def _conversation_turns(history: Sequence[ChatMessage]) -> list[tuple[ChatMessage, ...]]:
    turns: list[list[ChatMessage]] = []
    for message in history:
        if message.role is MessageRole.USER or not turns:
            turns.append([])
        turns[-1].append(message)
    return [tuple(turn) for turn in turns]


def _bound_message(message: ChatMessage, limit: int) -> ChatMessage:
    tool_calls = message.tool_calls
    tool_chars = sum(_tool_call_chars(call) for call in tool_calls)
    if tool_chars > limit // 2:
        tool_calls = tuple(_summarize_tool_call(call) for call in tool_calls)
        tool_chars = sum(_tool_call_chars(call) for call in tool_calls)
    content_limit = max(0, limit - tool_chars)
    return replace(
        message,
        content=_truncate_text(message.content, content_limit),
        tool_calls=tool_calls,
    )


def _summarize_tool_call(call: ModelToolCall) -> ModelToolCall:
    rendered = json.dumps(call.arguments, ensure_ascii=False, default=str)
    return replace(
        call,
        arguments={
            "_context_truncated": True,
            "original_chars": len(rendered),
        },
    )


def _tool_call_chars(call: ModelToolCall) -> int:
    return len(json.dumps(call.to_dict(), ensure_ascii=False, default=str))


def _message_context_chars(message: ChatMessage) -> int:
    return len(message.content) + sum(_tool_call_chars(call) for call in message.tool_calls)


def _truncate_text(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    if limit <= len(_TRUNCATION_MARKER):
        return content[:limit]
    available = limit - len(_TRUNCATION_MARKER)
    head = (available * 2) // 3
    tail = available - head
    return f"{content[:head]}{_TRUNCATION_MARKER}{content[-tail:]}"
