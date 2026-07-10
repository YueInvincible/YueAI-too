from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .audit import AuditLog
from .contracts import (
    ChatMessage,
    Conversation,
    ConversationStore,
    CoreEvent,
    MessageRole,
    ModelContext,
    ModelEventType,
    ModelRequest,
    ModelToolCall,
    ToolRequest,
    ToolStatus,
    utc_now,
)
from .context_window import ContextWindowPolicy
from .errors import YueCoreError
from .events import EventBus
from .providers import ModelProviderRegistry
from .tool_catalog import filter_tool_specs_for_role
from .tool_guidance import render_tool_guide_text
from .tools import ToolExecutor, ToolRegistry


class ConversationError(YueCoreError):
    pass


@dataclass(slots=True)
class _RunState:
    cancel_event: asyncio.Event
    task: asyncio.Task[Any]


class InMemoryConversationStore(ConversationStore):
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[ChatMessage]] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Conversation:
        conversation = Conversation(title=title, metadata=dict(metadata or {}))
        async with self._lock:
            self._conversations[conversation.id] = conversation
            self._messages[conversation.id] = []
        return conversation

    async def get(self, conversation_id: str) -> Conversation | None:
        async with self._lock:
            return self._conversations.get(conversation_id)

    async def list(self, *, limit: int = 100) -> Sequence[Conversation]:
        async with self._lock:
            conversations = sorted(
                self._conversations.values(),
                key=lambda item: item.updated_at,
                reverse=True,
            )
            return tuple(conversations[: max(0, limit)])

    async def append(self, message: ChatMessage) -> None:
        async with self._lock:
            conversation = self._conversations.get(message.conversation_id)
            if conversation is None:
                raise ConversationError(
                    f"Conversation does not exist: {message.conversation_id}"
                )
            self._messages[message.conversation_id].append(message)
            self._conversations[message.conversation_id] = replace(
                conversation,
                updated_at=utc_now(),
            )

    async def messages(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[ChatMessage]:
        async with self._lock:
            if conversation_id not in self._conversations:
                raise ConversationError(f"Conversation does not exist: {conversation_id}")
            messages = self._messages[conversation_id]
            if limit is None:
                return tuple(messages)
            return tuple(messages[-max(0, limit) :])


class SQLiteConversationStore(ConversationStore):
    """Durable conversation store using only the standard-library sqlite3."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._initialize_sync)
            self._initialized = True

    async def create(
        self,
        *,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Conversation:
        await self.initialize()
        conversation = Conversation(title=title, metadata=dict(metadata or {}))
        async with self._lock:
            await asyncio.to_thread(self._create_sync, conversation)
        return conversation

    async def get(self, conversation_id: str) -> Conversation | None:
        await self.initialize()
        async with self._lock:
            row = await asyncio.to_thread(self._get_sync, conversation_id)
        return self._conversation_from_row(row) if row else None

    async def list(self, *, limit: int = 100) -> Sequence[Conversation]:
        await self.initialize()
        async with self._lock:
            rows = await asyncio.to_thread(self._list_sync, max(0, limit))
        return tuple(self._conversation_from_row(row) for row in rows)

    async def append(self, message: ChatMessage) -> None:
        await self.initialize()
        async with self._lock:
            exists = await asyncio.to_thread(self._get_sync, message.conversation_id)
            if exists is None:
                raise ConversationError(
                    f"Conversation does not exist: {message.conversation_id}"
                )
            await asyncio.to_thread(self._append_sync, message)

    async def messages(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[ChatMessage]:
        await self.initialize()
        async with self._lock:
            exists = await asyncio.to_thread(self._get_sync, conversation_id)
            if exists is None:
                raise ConversationError(f"Conversation does not exist: {conversation_id}")
            rows = await asyncio.to_thread(self._messages_sync, conversation_id, limit)
        return tuple(self._message_from_row(row) for row in rows)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize_sync(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT NOT NULL UNIQUE,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls_json TEXT NOT NULL,
                    tool_call_id TEXT,
                    tool_name TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_sequence
                    ON messages(conversation_id, sequence);
                """
            )
            current = connection.execute(
                "SELECT value FROM schema_info WHERE key = 'version'"
            ).fetchone()
            if current is None:
                connection.execute(
                    "INSERT INTO schema_info(key, value) VALUES('version', ?)",
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(current["value"]) != self.SCHEMA_VERSION:
                raise ConversationError(
                    f"Unsupported conversation schema version: {current['value']}"
                )

    def _create_sync(self, conversation: Conversation) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO conversations(
                    id, title, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation.id,
                    conversation.title,
                    self._json(conversation.metadata),
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                ),
            )

    def _get_sync(self, conversation_id: str):
        with self._connection() as connection:
            return connection.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()

    def _list_sync(self, limit: int):
        with self._connection() as connection:
            return connection.execute(
                """
                SELECT * FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def _append_sync(self, message: ChatMessage) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO messages(
                    id, conversation_id, role, content, tool_calls_json,
                    tool_call_id, tool_name, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.conversation_id,
                    message.role.value,
                    message.content,
                    self._json([call.to_dict() for call in message.tool_calls]),
                    message.tool_call_id,
                    message.tool_name,
                    self._json(message.metadata),
                    message.created_at.isoformat(),
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (utc_now().isoformat(), message.conversation_id),
            )

    def _messages_sync(self, conversation_id: str, limit: int | None):
        with self._connection() as connection:
            if limit is None:
                return connection.execute(
                    """
                    SELECT * FROM messages
                    WHERE conversation_id = ?
                    ORDER BY sequence ASC
                    """,
                    (conversation_id,),
                ).fetchall()
            rows = connection.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY sequence DESC
                LIMIT ?
                """,
                (conversation_id, max(0, int(limit))),
            ).fetchall()
            return list(reversed(rows))

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))

    @staticmethod
    def _conversation_from_row(row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            title=row["title"],
            metadata=json.loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> ChatMessage:
        calls = tuple(
            ModelToolCall(
                id=item["id"],
                name=item["name"],
                arguments=item["arguments"],
            )
            for item in json.loads(row["tool_calls_json"])
        )
        return ChatMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            tool_calls=calls,
            tool_call_id=row["tool_call_id"],
            tool_name=row["tool_name"],
            metadata=json.loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class ConversationOrchestrator:
    def __init__(
        self,
        store: ConversationStore,
        providers: ModelProviderRegistry,
        tools: ToolRegistry,
        executor: ToolExecutor,
        events: EventBus,
        audit: AuditLog,
        *,
        default_provider: str,
        routes: Mapping[str, Mapping[str, str]] | None = None,
        prompt_profiles: Mapping[str, Mapping[str, str]] | None = None,
        max_tool_iterations: int = 4,
        max_tool_output_chars: int = 12000,
        context_policy: ContextWindowPolicy | None = None,
    ) -> None:
        self.store = store
        self.providers = providers
        self.tools = tools
        self.executor = executor
        self.events = events
        self.audit = audit
        self.default_provider = default_provider
        self.routes = {str(key): dict(value) for key, value in (routes or {}).items()}
        self.prompt_profiles = {
            str(key): dict(value) for key, value in (prompt_profiles or {}).items()
        }
        self.max_tool_iterations = max_tool_iterations
        self.max_tool_output_chars = max_tool_output_chars
        self.context_policy = context_policy or ContextWindowPolicy()
        self._runs: dict[str, _RunState] = {}
        self._conversation_locks: dict[str, asyncio.Lock] = {}
        self._accepting = True

    def resume(self) -> None:
        self._accepting = True

    async def create(
        self,
        *,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Conversation:
        conversation = await self.store.create(title=title, metadata=metadata)
        await self.audit.write(
            "conversation.created",
            {"conversation_id": conversation.id, "has_title": title is not None},
        )
        await self.events.publish(
            CoreEvent(
                "conversation.created",
                conversation.to_dict(),
                correlation_id=conversation.id,
            )
        )
        return conversation

    async def send(
        self,
        conversation_id: str,
        content: str,
        *,
        provider_name: str | None = None,
        provider_role: str = "chat",
        run_id: str | None = None,
        actor: str = "user",
    ) -> ChatMessage:
        if not self._accepting:
            raise ConversationError("Conversation orchestrator is shutting down")
        if not content.strip():
            raise ConversationError("Message content cannot be empty")
        if await self.store.get(conversation_id) is None:
            raise ConversationError(f"Conversation does not exist: {conversation_id}")

        return await self._execute_run(
            conversation_id,
            content,
            provider_name=provider_name,
            provider_role=provider_role,
            run_id=run_id,
            actor=actor,
            append_user_message=True,
        )

    async def resume_run(
        self,
        conversation_id: str,
        *,
        provider_name: str | None = None,
        provider_role: str = "coding_agent",
        run_id: str,
        actor: str = "user",
    ) -> ChatMessage:
        if not self._accepting:
            raise ConversationError("Conversation orchestrator is shutting down")
        if await self.store.get(conversation_id) is None:
            raise ConversationError(f"Conversation does not exist: {conversation_id}")
        return await self._execute_run(
            conversation_id,
            "",
            provider_name=provider_name,
            provider_role=provider_role,
            run_id=run_id,
            actor=actor,
            append_user_message=False,
        )

    async def _execute_run(
        self,
        conversation_id: str,
        content: str,
        *,
        provider_name: str | None,
        provider_role: str,
        run_id: str | None,
        actor: str,
        append_user_message: bool,
    ) -> ChatMessage:

        run_id = run_id or str(uuid4())
        if run_id in self._runs:
            raise ConversationError(f"Run id is already active: {run_id}")
        cancel_event = asyncio.Event()
        current_task = asyncio.current_task()
        if current_task is None:
            raise ConversationError("Conversation must run inside an asyncio task")
        self._runs[run_id] = _RunState(cancel_event, current_task)
        lock = self._conversation_locks.setdefault(conversation_id, asyncio.Lock())
        try:
            async with lock:
                return await self._run(
                    conversation_id,
                    content,
                    self.resolve_provider(
                        provider_name=provider_name,
                        provider_role=provider_role,
                    ),
                    provider_role,
                    run_id,
                    actor,
                    cancel_event,
                    append_user_message=append_user_message,
                )
        finally:
            self._runs.pop(run_id, None)

    def cancel(self, run_id: str) -> bool:
        state = self._runs.get(run_id)
        if state is None:
            return False
        state.cancel_event.set()
        state.task.cancel()
        return True

    async def shutdown(self) -> None:
        self._accepting = False
        current = asyncio.current_task()
        tasks = []
        for state in list(self._runs.values()):
            state.cancel_event.set()
            if state.task is not current:
                state.task.cancel()
                tasks.append(state.task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(
        self,
        conversation_id: str,
        content: str,
        provider_name: str,
        provider_role: str,
        run_id: str,
        actor: str,
        cancel_event: asyncio.Event,
        *,
        append_user_message: bool = True,
    ) -> ChatMessage:
        provider = self.providers.get(provider_name)
        if append_user_message:
            user_message = ChatMessage(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=content,
                metadata={"actor": actor, "run_id": run_id},
            )
            await self._append(user_message, run_id)
        await self.events.publish(
            CoreEvent(
                "conversation.run.started",
                {
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    "provider": provider_name,
                    "provider_role": provider_role,
                    "prompt_profile": self.resolve_prompt_profile(provider_role),
                },
                correlation_id=run_id,
            )
        )
        await self.audit.write(
            "conversation.run.started",
            {
                "run_id": run_id,
                "conversation_id": conversation_id,
                "provider": provider_name,
                "provider_role": provider_role,
                "prompt_profile": self.resolve_prompt_profile(provider_role),
            },
        )

        try:
            for iteration in range(self.max_tool_iterations + 1):
                self._raise_if_cancelled(cancel_event)
                history = self.context_policy.bound_history(
                    await self.store.messages(conversation_id)
                )
                request = ModelRequest(
                    conversation_id=conversation_id,
                    messages=self._request_messages(
                        conversation_id,
                        history,
                        provider_role=provider_role,
                    ),
                    tools=self._model_tools(provider_role),
                    run_id=run_id,
                )
                text_parts: list[str] = []
                tool_calls: list[ModelToolCall] = []
                saw_finish = False
                context = ModelContext(
                    cancelled=cancel_event.is_set,
                    publish=self.events.publish,
                )
                async for event in provider.generate(request, context):
                    self._raise_if_cancelled(cancel_event)
                    if event.type is ModelEventType.TEXT_DELTA:
                        if event.text:
                            text_parts.append(event.text)
                            await self.events.publish(
                                CoreEvent(
                                    "conversation.delta",
                                    {
                                        "run_id": run_id,
                                        "conversation_id": conversation_id,
                                        "text": event.text,
                                    },
                                    source=provider_name,
                                    correlation_id=run_id,
                                )
                            )
                    elif event.type is ModelEventType.TOOL_CALL:
                        if event.tool_call is None:
                            raise ConversationError("Provider emitted an empty tool call")
                        tool_calls.append(event.tool_call)
                    elif event.type is ModelEventType.FINISH:
                        saw_finish = True
                    else:
                        raise ConversationError(f"Unsupported model event: {event.type}")

                assistant = ChatMessage(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content="".join(text_parts),
                    tool_calls=tuple(tool_calls),
                    metadata={
                        "provider": provider_name,
                        "provider_role": provider_role,
                        "prompt_profile": self.resolve_prompt_profile(provider_role),
                        "run_id": run_id,
                    },
                )
                call_ids = [call.id for call in tool_calls]
                if len(call_ids) != len(set(call_ids)):
                    raise ConversationError("Provider emitted duplicate tool-call ids")
                await self._append(assistant, run_id)

                if not tool_calls:
                    await self.audit.write(
                        "conversation.run.completed",
                        {
                            "run_id": run_id,
                            "conversation_id": conversation_id,
                            "provider": provider_name,
                            "provider_role": provider_role,
                            "tool_iterations": iteration,
                            "response_chars": len(assistant.content),
                        },
                    )
                    await self.events.publish(
                        CoreEvent(
                            "conversation.run.completed",
                            {
                                "run_id": run_id,
                                "conversation_id": conversation_id,
                                "message": assistant.to_dict(),
                                "finish_seen": saw_finish,
                            },
                            correlation_id=run_id,
                        )
                    )
                    return assistant

                if iteration >= self.max_tool_iterations:
                    raise ConversationError(
                        f"Tool iteration limit reached ({self.max_tool_iterations})"
                    )

                tool_requests = [
                    ToolRequest(
                        call.name,
                        call.arguments,
                        actor="model",
                        session_id=conversation_id,
                        metadata={
                            "run_id": run_id,
                            "conversation_id": conversation_id,
                            "tool_call_id": call.id,
                        },
                    )
                    for call in tool_calls
                ]
                for call, tool_request in zip(tool_calls, tool_requests, strict=False):
                    self._raise_if_cancelled(cancel_event)
                    await self.events.publish(
                        CoreEvent(
                            "conversation.tool.requested",
                            {
                                "run_id": run_id,
                                "conversation_id": conversation_id,
                                "request_id": tool_request.id,
                                "tool_call": call.to_dict(),
                            },
                            correlation_id=run_id,
                        )
                    )
                results = await self.executor.execute_many(
                    tool_requests,
                    parallel=self._can_run_parallel_tool_batch(tool_calls),
                )
                for call, result in zip(tool_calls, results, strict=False):
                    tool_message = ChatMessage(
                        conversation_id=conversation_id,
                        role=MessageRole.TOOL,
                        content=self._bounded_tool_result(result),
                        tool_call_id=call.id,
                        tool_name=call.name,
                        metadata={"status": result.status.value, "run_id": run_id},
                    )
                    await self._append(tool_message, run_id)
                    await self.events.publish(
                        CoreEvent(
                            "conversation.tool.completed",
                            {
                                "run_id": run_id,
                                "conversation_id": conversation_id,
                                "tool_call_id": call.id,
                                "tool": call.name,
                                "status": result.status.value,
                            },
                            correlation_id=run_id,
                        )
                    )
            raise ConversationError("Conversation loop ended unexpectedly")
        except asyncio.CancelledError:
            cancel_event.set()
            await self.audit.write(
                "conversation.run.cancelled",
                {"run_id": run_id, "conversation_id": conversation_id},
            )
            await self._publish_cancelled(conversation_id, run_id)
            raise
        except ConversationError as exc:
            if cancel_event.is_set():
                await self.audit.write(
                    "conversation.run.cancelled",
                    {"run_id": run_id, "conversation_id": conversation_id},
                )
                await self._publish_cancelled(conversation_id, run_id)
            else:
                await self.audit.write(
                    "conversation.run.failed",
                    {
                        "run_id": run_id,
                        "conversation_id": conversation_id,
                        "error_type": type(exc).__name__,
                    },
                )
                await self.events.publish(
                    CoreEvent(
                        "conversation.run.failed",
                        {
                            "run_id": run_id,
                            "conversation_id": conversation_id,
                            "error": str(exc),
                        },
                        correlation_id=run_id,
                    )
                )
            raise
        except Exception as exc:
            await self.audit.write(
                "conversation.run.failed",
                {
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    "error_type": type(exc).__name__,
                },
            )
            await self.events.publish(
                CoreEvent(
                    "conversation.run.failed",
                    {
                        "run_id": run_id,
                        "conversation_id": conversation_id,
                        "error": str(exc),
                    },
                    correlation_id=run_id,
                )
            )
            raise

    async def _append(self, message: ChatMessage, run_id: str) -> None:
        await self.store.append(message)
        await self.events.publish(
            CoreEvent(
                "conversation.message.appended",
                {"run_id": run_id, "message": message.to_dict()},
                correlation_id=run_id,
            )
        )

    async def _publish_cancelled(self, conversation_id: str, run_id: str) -> None:
        await self.events.publish(
            CoreEvent(
                "conversation.run.cancelled",
                {"run_id": run_id, "conversation_id": conversation_id},
                correlation_id=run_id,
            )
        )

    @staticmethod
    def _raise_if_cancelled(cancel_event: asyncio.Event) -> None:
        if cancel_event.is_set():
            raise asyncio.CancelledError

    def _bounded_tool_result(self, result) -> str:
        payload = self._tool_result_payload(result)
        rendered = json.dumps(payload, ensure_ascii=False, default=str)
        if len(rendered) <= self.max_tool_output_chars:
            return rendered
        marker = "...[truncated]"
        return rendered[: self.max_tool_output_chars - len(marker)] + marker

    def _can_run_parallel_tool_batch(
        self,
        tool_calls: Sequence[ModelToolCall],
    ) -> bool:
        if len(tool_calls) < 2:
            return False
        for call in tool_calls:
            spec = self.tools.get(call.name)
            if not bool(spec.spec.metadata.get("parallel_safe", False)):
                return False
            if bool(spec.spec.metadata.get("mutates_state", False)):
                return False
        return True

    @staticmethod
    def _tool_result_payload(result) -> dict[str, Any]:
        return {
            "request_id": result.request_id,
            "tool_name": result.tool_name,
            "ok": result.status is ToolStatus.SUCCEEDED,
            "status": result.status.value,
            "output": result.output if result.status is ToolStatus.SUCCEEDED else None,
            "error": result.error,
        }

    def _model_tools(self, provider_role: str):
        return self.context_policy.bound_tools(
            filter_tool_specs_for_role(self.tools.list_specs(), provider_role)
        )

    def prompt_preview(self, provider_role: str = "chat") -> dict[str, Any]:
        return {
            "provider_role": provider_role,
            "prompt_profile": self.resolve_prompt_profile(provider_role),
            "system_instruction": self._system_instruction(provider_role),
            "tool_count": len(self._model_tools(provider_role)),
        }

    def resolve_provider(
        self,
        *,
        provider_name: str | None = None,
        provider_role: str = "chat",
    ) -> str:
        if provider_name:
            return provider_name
        route = self.routes.get(provider_role) or {}
        return str(route.get("provider") or self.default_provider)

    def resolve_prompt_profile(self, provider_role: str) -> str:
        route = self.routes.get(provider_role) or {}
        prompt_profile = str(route.get("prompt_profile") or "")
        if prompt_profile:
            return prompt_profile
        if provider_role in self.prompt_profiles:
            return provider_role
        return "default"

    def _request_messages(
        self,
        conversation_id: str,
        history: Sequence[ChatMessage],
        *,
        provider_role: str,
    ) -> Sequence[ChatMessage]:
        system_instruction = self.context_policy.bound_system_instruction(
            self._system_instruction(provider_role)
        )
        if not system_instruction:
            return history
        return (
            ChatMessage(
                conversation_id=conversation_id,
                role=MessageRole.SYSTEM,
                content=system_instruction,
                metadata={
                    "internal": True,
                    "prompt_profile": self.resolve_prompt_profile(provider_role),
                    "provider_role": provider_role,
                },
            ),
            *history,
        )

    def _system_instruction(self, provider_role: str) -> str:
        prompt_profile = self.resolve_prompt_profile(provider_role)
        profile = self.prompt_profiles.get(prompt_profile, {})
        tool_instruction = profile.get("tool_instruction", "").strip()
        if provider_role == "coding_agent":
            guide = render_tool_guide_text(self._model_tools(provider_role), provider_role=provider_role)
            if guide:
                tool_instruction = (
                    f"{tool_instruction}\n\n{guide}" if tool_instruction else guide
                )
        parts = [
            ("System", profile.get("system_instruction", "").strip()),
            ("Personality", profile.get("personality", "").strip()),
            ("Tool usage", tool_instruction),
            ("Response style", profile.get("response_instruction", "").strip()),
        ]
        sections = [f"{label}:\n{value}" for label, value in parts if value]
        return "\n\n".join(sections)
