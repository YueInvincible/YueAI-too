from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .audit import AuditLog
from .contracts import (
    CoreEvent,
    PermissionOutcome,
    Tool,
    ToolContext,
    ToolOutputKind,
    ToolRequest,
    ToolResult,
    ToolSpec,
    ToolStatus,
)
from .errors import ToolRegistrationError
from .events import EventBus
from .permissions import PermissionEngine
from .schema import validate, validate_schema
from .builtin_tools import _sanitize_command_output


_COMMAND_STYLE_STRING_KEYS = frozenset({"stdout", "stderr", "status", "diff"})
_FILE_CONTENT_STRING_KEYS = frozenset({"content"})


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        spec = tool.spec
        if not spec.name or ("." not in spec.name and "_" not in spec.name):
            raise ToolRegistrationError(
                "Tool names must be namespaced or stable aliases, e.g. file.read or ask_user_approval"
            )
        if spec.name in self._tools:
            raise ToolRegistrationError(f"Tool already registered: {spec.name}")
        validate_schema(spec.input_schema)
        self._tools[spec.name] = tool

    def unregister_plugin(self, plugin_id: str) -> None:
        self._tools = {
            name: tool
            for name, tool in self._tools.items()
            if tool.spec.plugin_id != plugin_id
        }

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def list_specs(self) -> list[ToolSpec]:
        return [self._tools[name].spec for name in sorted(self._tools)]


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        permissions: PermissionEngine,
        events: EventBus,
        audit: AuditLog,
        *,
        default_timeout_seconds: float = 30.0,
        services: Mapping[str, Any] | None = None,
    ) -> None:
        self.registry = registry
        self.permissions = permissions
        self.events = events
        self.audit = audit
        self.default_timeout_seconds = default_timeout_seconds
        self.services = services or {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def cancel(self, request_id: str) -> bool:
        event = self._cancel_events.get(request_id)
        if event is None:
            return False
        event.set()
        return True

    async def execute_many(
        self,
        requests: list[ToolRequest],
        *,
        parallel: bool = False,
    ) -> list[ToolResult]:
        if not parallel:
            return [await self.execute(request) for request in requests]
        specs = [self.registry.get(request.tool_name).spec for request in requests]
        for spec in specs:
            if not bool(spec.metadata.get("parallel_safe", False)):
                raise ValueError(f"Tool is not marked parallel_safe: {spec.name}")
            if bool(spec.metadata.get("mutates_state", False)):
                raise ValueError(f"State-changing tool cannot run in parallel: {spec.name}")
        return list(await asyncio.gather(*(self.execute(request) for request in requests)))

    async def execute(self, request: ToolRequest) -> ToolResult:
        started = datetime.now(UTC)
        await self.audit.write(
            "tool.request",
            {
                "request_id": request.id,
                "tool": request.tool_name,
                "actor": request.actor,
                "session_id": request.session_id,
                "argument_keys": sorted(request.arguments),
            },
        )
        try:
            tool = self.registry.get(request.tool_name)
        except KeyError as exc:
            result = self._result(request, ToolStatus.FAILED, started, error=str(exc))
            await self._finish(request, result)
            return result

        try:
            validate(request.arguments, tool.spec.input_schema)
        except Exception as exc:
            result = self._result(request, ToolStatus.FAILED, started, error=str(exc))
            await self._finish(request, result)
            return result

        decision = await self.permissions.evaluate(request, tool.spec)
        await self.audit.write(
            "permission.decision",
            {
                "request_id": request.id,
                "tool": request.tool_name,
                "outcome": decision.outcome.value,
                "reason": decision.reason,
                "rule_id": decision.rule_id,
                "denial_category": (
                    decision.denial_category.value
                    if decision.denial_category is not None
                    else None
                ),
                "resource_scope": dict(decision.resource_scope),
            },
        )
        if decision.outcome is not PermissionOutcome.ALLOW:
            result = self._result(
                request,
                ToolStatus.DENIED,
                started,
                error=decision.reason,
                metadata={
                    "permission": {
                        "outcome": decision.outcome.value,
                        "reason": decision.reason,
                        "rule_id": decision.rule_id,
                        "denial_category": (
                            decision.denial_category.value
                            if decision.denial_category is not None
                            else None
                        ),
                        "resource_scope": dict(decision.resource_scope),
                    }
                },
            )
            await self._finish(request, result)
            return result

        cancel_event = asyncio.Event()
        self._cancel_events[request.id] = cancel_event
        context = ToolContext(
            request=request,
            publish=self.events.publish,
            cancelled=cancel_event.is_set,
            services=self.services,
        )
        await self.events.publish(
            CoreEvent(
                "tool.started",
                self._event_payload(request),
                correlation_id=request.id,
            )
        )

        timeout = tool.spec.timeout_seconds or self.default_timeout_seconds
        try:
            async with asyncio.timeout(timeout):
                output = await tool.invoke(request.arguments, context)
            output = self._sanitize_output(tool.spec, output)
            status = ToolStatus.CANCELLED if cancel_event.is_set() else ToolStatus.SUCCEEDED
            result = self._result(request, status, started, output=output)
        except TimeoutError:
            cancel_event.set()
            result = self._result(
                request,
                ToolStatus.TIMED_OUT,
                started,
                error=f"Tool exceeded {timeout:g}s timeout",
            )
        except asyncio.CancelledError:
            cancel_event.set()
            result = self._result(request, ToolStatus.CANCELLED, started, error="Cancelled")
        except Exception as exc:
            result = self._result(request, ToolStatus.FAILED, started, error=str(exc))
        finally:
            self._cancel_events.pop(request.id, None)

        await self._finish(request, result)
        return result

    async def _finish(self, request: ToolRequest, result: ToolResult) -> None:
        await self.audit.write(
            "tool.result",
            {
                "request_id": result.request_id,
                "tool": result.tool_name,
                "status": result.status.value,
                "error": result.error,
                "metadata": dict(result.metadata),
                "output_type": type(result.output).__name__,
                "duration_ms": round(
                    (result.finished_at - result.started_at).total_seconds() * 1000,
                    3,
                ),
            },
        )
        await self.events.publish(
            CoreEvent(
                "tool.finished",
                {
                    **result.to_dict(),
                    **self._event_payload(request),
                },
                correlation_id=request.id,
            )
        )

    @staticmethod
    def _result(
        request: ToolRequest,
        status: ToolStatus,
        started: datetime,
        *,
        output: Any = None,
        error: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ToolResult:
        return ToolResult(
            request_id=request.id,
            tool_name=request.tool_name,
            status=status,
            output=output,
            error=error,
            metadata=dict(metadata or {}),
            started_at=started,
            finished_at=datetime.now(UTC),
        )

    @classmethod
    def _sanitize_output(cls, spec: ToolSpec, output: Any) -> Any:
        if spec.output_kind is ToolOutputKind.COMMAND_OUTPUT:
            return cls._sanitize_command_payload(output)
        if spec.output_kind is ToolOutputKind.FILE_CONTENT:
            return cls._sanitize_file_content_payload(output)
        return output

    @classmethod
    def _sanitize_command_payload(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            sanitized = dict(value)
            for key, item in list(sanitized.items()):
                if isinstance(item, str) and key in _COMMAND_STYLE_STRING_KEYS:
                    cleaned, truncated = _sanitize_command_output(item)
                    sanitized[key] = cleaned
                    truncated_key = "truncated" if key in {"status", "diff"} else f"{key}_truncated"
                    if truncated:
                        sanitized[truncated_key] = bool(sanitized.get(truncated_key, False)) or truncated
                else:
                    sanitized[key] = cls._sanitize_command_payload(item)
            return sanitized
        if isinstance(value, list):
            return [cls._sanitize_command_payload(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._sanitize_command_payload(item) for item in value)
        return value

    @classmethod
    def _sanitize_file_content_payload(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            sanitized = dict(value)
            returned_lines_override: int | None = None
            for key, item in list(sanitized.items()):
                if isinstance(item, str) and key in _FILE_CONTENT_STRING_KEYS:
                    cleaned, truncated = _sanitize_command_output(item)
                    sanitized[key] = cleaned
                    if truncated:
                        sanitized["truncated"] = bool(sanitized.get("truncated", False)) or truncated
                    returned_lines_override = len(cleaned.splitlines()) if cleaned else 0
                else:
                    sanitized[key] = cls._sanitize_file_content_payload(item)
            if returned_lines_override is not None:
                sanitized["returned_lines"] = returned_lines_override
            return sanitized
        if isinstance(value, list):
            return [cls._sanitize_file_content_payload(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._sanitize_file_content_payload(item) for item in value)
        return value

    @staticmethod
    def _event_payload(request: ToolRequest) -> dict[str, Any]:
        payload = {
            "request_id": request.id,
            "tool": request.tool_name,
        }
        for key in ("run_id", "conversation_id", "tool_call_id"):
            if key in request.metadata:
                payload[key] = request.metadata[key]
        return payload
