"""Stable public contracts for Yue Core plugins and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from collections.abc import AsyncIterator, Sequence
from typing import Any, Awaitable, Callable, Mapping, Protocol
from uuid import uuid4

CORE_API_VERSION = "1.1"
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
EventHandler = Callable[["CoreEvent"], Awaitable[None]]


def utc_now() -> datetime:
    return datetime.now(UTC)


class Capability(str, Enum):
    CORE_READ = "core.read"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    PROCESS_READ = "process.read"
    PROCESS_CONTROL = "process.control"
    SCREEN_CAPTURE = "screen.capture"
    NETWORK_ACCESS = "network.access"
    SHELL_EXECUTE = "shell.execute"
    SYSTEM_ADMIN = "system.admin"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class ToolStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ModelEventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    FINISH = "finish"


class DesktopPresence(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    TOOL_WORKING = "tool_working"
    SLEEPING = "sleeping"


class AvatarExpression(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"


class DesktopCommand(str, Enum):
    AVATAR_CLICK = "avatar.click"
    HOTKEY_TOGGLE_CONSOLE = "hotkey.toggle_console"
    CONSOLE_OPEN = "console.open"
    CONSOLE_CLOSE = "console.close"
    CONSOLE_TOGGLE = "console.toggle"
    SET_PRESENCE = "presence.set"
    SET_EXPRESSION = "expression.set"
    SLEEP = "avatar.sleep"
    WAKE = "avatar.wake"


@dataclass(frozen=True, slots=True)
class CoreEvent:
    topic: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    source: str = "core"
    correlation_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": dict(self.payload),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Mapping[str, Any]
    capability: Capability = Capability.CORE_READ
    risk: RiskLevel = RiskLevel.LOW
    timeout_seconds: float | None = None
    plugin_id: str = "core"


@dataclass(frozen=True, slots=True)
class ToolRequest:
    tool_name: str
    arguments: Mapping[str, Any]
    actor: str = "user"
    session_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ToolResult:
    request_id: str
    tool_name: str
    status: ToolStatus
    output: Any = None
    error: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime = field(default_factory=utc_now)

    @property
    def ok(self) -> bool:
        return self.status is ToolStatus.SUCCEEDED

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ModelToolCall:
    name: str
    arguments: Mapping[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "arguments": dict(self.arguments)}


@dataclass(frozen=True, slots=True)
class ChatMessage:
    conversation_id: str
    role: MessageRole
    content: str = ""
    tool_calls: tuple[ModelToolCall, ...] = ()
    tool_call_id: str | None = None
    tool_name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role.value,
            "content": self.content,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class Conversation:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class DesktopState:
    attached_session_ids: tuple[str, ...] = ()
    console_open: bool = False
    presence: DesktopPresence = DesktopPresence.IDLE
    expression: AvatarExpression = AvatarExpression.NEUTRAL
    hotkey: str = "Ctrl+Shift+Y"
    model_path: str | None = None
    window_anchor: str = "bottom-right"
    click_opens_console: bool = True
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attached_session_ids": list(self.attached_session_ids),
            "console_open": self.console_open,
            "presence": self.presence.value,
            "expression": self.expression.value,
            "hotkey": self.hotkey,
            "model_path": self.model_path,
            "window_anchor": self.window_anchor,
            "click_opens_console": self.click_opens_console,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ModelRequest:
    conversation_id: str
    messages: Sequence[ChatMessage]
    tools: Sequence[ToolSpec]
    run_id: str


@dataclass(frozen=True, slots=True)
class ModelEvent:
    type: ModelEventType
    text: str = ""
    tool_call: ModelToolCall | None = None
    finish_reason: str | None = None


@dataclass(slots=True)
class ModelContext:
    cancelled: Callable[[], bool]
    publish: Callable[[CoreEvent], Awaitable[None]]


class ModelProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def generate(
        self,
        request: ModelRequest,
        context: ModelContext,
    ) -> AsyncIterator[ModelEvent]: ...

    async def health(self) -> Mapping[str, Any]: ...


class ConversationStore(Protocol):
    async def create(
        self,
        *,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Conversation: ...

    async def get(self, conversation_id: str) -> Conversation | None: ...

    async def list(self, *, limit: int = 100) -> Sequence[Conversation]: ...

    async def append(self, message: ChatMessage) -> None: ...

    async def messages(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[ChatMessage]: ...


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    outcome: PermissionOutcome
    reason: str
    rule_id: str | None = None


@dataclass(slots=True)
class ToolContext:
    request: ToolRequest
    publish: Callable[[CoreEvent], Awaitable[None]]
    cancelled: Callable[[], bool]
    services: Mapping[str, Any] = field(default_factory=dict)


class Tool(Protocol):
    @property
    def spec(self) -> ToolSpec: ...

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any: ...


class PluginContext(Protocol):
    plugin_id: str
    config: Mapping[str, Any]

    def register_tool(self, tool: Tool) -> None: ...

    def register_service(self, name: str, service: Any) -> None: ...

    def register_model_provider(self, provider: ModelProvider) -> None: ...

    def subscribe(self, topic: str, handler: EventHandler) -> Callable[[], None]: ...

    async def publish(self, event: CoreEvent) -> None: ...

    def get_service(self, name: str) -> Any: ...


class Plugin(Protocol):
    async def setup(self, context: PluginContext) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


class Service(Protocol):
    """Optional lifecycle contract for long-running provider services."""

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def health(self) -> Mapping[str, Any]: ...
