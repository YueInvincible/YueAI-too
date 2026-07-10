from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .agent_runs import AgentRun
from .contracts import ChatMessage, MessageRole


@dataclass(frozen=True, slots=True)
class AgentRunResumeAnalysis:
    has_persisted_input: bool
    completed_message: ChatMessage | None
    missing_tool_result_ids: tuple[str, ...]

    @property
    def safe_to_resume(self) -> bool:
        return not self.missing_tool_result_ids


def analyze_agent_run_resume(
    run: AgentRun,
    messages: Sequence[ChatMessage],
) -> AgentRunResumeAnalysis:
    run_messages = tuple(
        message
        for message in messages
        if str(message.metadata.get("run_id", "")) == run.id
    )
    has_persisted_input = any(
        message.role is MessageRole.USER for message in run_messages
    )
    if not has_persisted_input:
        # Runs created before user messages carried run_id can still be resumed
        # without duplicating the request when their durable timestamp/content
        # identify the input unambiguously enough.
        has_persisted_input = any(
            message.role is MessageRole.USER
            and message.content == run.user_request
            and message.created_at >= run.created_at
            for message in messages
        )

    completed_message = next(
        (
            message
            for message in reversed(run_messages)
            if message.role is MessageRole.ASSISTANT and not message.tool_calls
        ),
        None,
    )
    requested_tool_ids = {
        call.id
        for message in run_messages
        if message.role is MessageRole.ASSISTANT
        for call in message.tool_calls
    }
    completed_tool_ids = {
        str(message.tool_call_id)
        for message in run_messages
        if message.role is MessageRole.TOOL and message.tool_call_id
    }
    return AgentRunResumeAnalysis(
        has_persisted_input=has_persisted_input,
        completed_message=completed_message,
        missing_tool_result_ids=tuple(sorted(requested_tool_ids - completed_tool_ids)),
    )
