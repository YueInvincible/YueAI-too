from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, TextIO
from uuid import uuid4

from .app import YueCore
from .contracts import CoreEvent, PermissionOutcome
from .tool_catalog import filter_tool_specs_for_role
from .tool_guidance import build_tool_guide, render_tool_guide_text


class JsonLineServer:
    """Minimal local transport for UI/sidecar integration."""

    def __init__(
        self,
        core: YueCore,
        *,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        self.core = core
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._write_lock = asyncio.Lock()

    async def serve(self) -> None:
        async with self.core:
            pending: set[asyncio.Task[None]] = set()

            async def forward_event(event: CoreEvent) -> None:
                await self._write({"event": event.to_dict()})

            unsubscribes = [
                self.core.events.subscribe("conversation.*", forward_event),
                self.core.events.subscribe("desktop.*", forward_event),
                self.core.events.subscribe("approval.*", forward_event),
                self.core.events.subscribe("tool.*", forward_event),
            ]
            try:
                while True:
                    line = await asyncio.to_thread(self.stdin.readline)
                    if line == "":
                        break
                    line = line.lstrip("\ufeff").strip()
                    if not line:
                        continue
                    task = asyncio.create_task(self._handle_and_write(line))
                    pending.add(task)
                    task.add_done_callback(pending.discard)
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
            finally:
                for unsubscribe in unsubscribes:
                    unsubscribe()

    async def _handle_and_write(self, line: str) -> None:
        await self._write(await self.handle_line(line))

    async def handle_line(self, line: str) -> dict[str, Any]:
        try:
            line = line.lstrip("\ufeff").strip()
            message = json.loads(line)
            message_id = message.get("id")
            method = message["method"]
            params = message.get("params", {})
            if method == "core.health":
                result = await self.core.invoke("core.health", {})
                payload = result.to_dict()
            elif method == "tools.list":
                provider_role = params.get("provider_role")
                specs = filter_tool_specs_for_role(
                    self.core.registry.list_specs(),
                    str(provider_role) if provider_role is not None else None,
                )
                payload = [
                    {
                        "name": spec.name,
                        "description": spec.description,
                        "model_description": spec.model_description(),
                        "input_schema": spec.input_schema,
                        "capability": spec.capability.value,
                        "risk": spec.risk.value,
                        "plugin_id": spec.plugin_id,
                        "output_kind": spec.output_kind.value,
                        "metadata": spec.runtime_metadata(),
                    }
                    for spec in specs
                ]
            elif method == "tools.guide":
                provider_role = params.get("provider_role")
                specs = filter_tool_specs_for_role(
                    self.core.registry.list_specs(),
                    str(provider_role) if provider_role is not None else None,
                )
                payload = build_tool_guide(
                    specs,
                    provider_role=str(provider_role) if provider_role is not None else None,
                )
                payload["text"] = render_tool_guide_text(
                    specs,
                    provider_role=str(provider_role) if provider_role is not None else None,
                )
            elif method == "tools.invoke":
                result = await self.core.invoke(
                    params["name"],
                    params.get("arguments", {}),
                    actor=params.get("actor", "ui"),
                    session_id=params.get("session_id"),
                )
                payload = result.to_dict()
            elif method == "tools.invoke_many":
                calls = params.get("calls", [])
                if not isinstance(calls, list) or not calls:
                    raise ValueError("calls must be a non-empty array")
                requests = [
                    (
                        call["name"],
                        call.get("arguments", {}),
                    )
                    for call in calls
                ]
                results = await self.core.invoke_many(
                    requests,
                    actor=params.get("actor", "ui"),
                    session_id=params.get("session_id"),
                    parallel=bool(params.get("parallel", False)),
                )
                payload = {
                    "parallel": bool(params.get("parallel", False)),
                    "results": [result.to_dict() for result in results],
                }
            elif method == "tools.cancel":
                payload = {"cancelled": self.core.executor.cancel(params["request_id"])}
            elif method == "approval.request":
                result = await self.core.invoke(
                    "approval.request",
                    {
                        "action_description": params["action_description"],
                        "risk_level": params["risk_level"],
                    },
                    actor=params.get("actor", "ui"),
                    session_id=params.get("session_id"),
                )
                payload = result.to_dict()
            elif method == "approval.pending.list":
                approvals = self.core.services.get("core.approvals")
                if approvals is None or not hasattr(approvals, "list_pending"):
                    raise RuntimeError("approval bridge is not available")
                payload = await approvals.list_pending()
            elif method == "approval.respond":
                approvals = self.core.services.get("core.approvals")
                if approvals is None or not hasattr(approvals, "respond"):
                    raise RuntimeError("approval bridge is not available")
                payload = await approvals.respond(
                    params["approval_id"],
                    bool(params["approved"]),
                )
            elif method == "tool.activity.snapshot":
                tool_activity = self.core.services.get("core.tool_activity")
                if tool_activity is None or not hasattr(tool_activity, "snapshot"):
                    raise RuntimeError("tool activity store is not available")
                payload = await tool_activity.snapshot()
            elif method == "permissions.allow_all_cmd.get":
                grants = self.core.services.get("core.permission_grants")
                if grants is None or not hasattr(grants, "get"):
                    raise RuntimeError("permission grant store is not available")
                session_id = params["session_id"]
                grant = grants.get(session_id)
                payload = (
                    grant.to_dict()
                    if grant is not None
                    else {
                        "session_id": session_id,
                        "allow_all_cmd": False,
                        "updated_by": "none",
                    }
                )
            elif method == "permissions.allow_all_cmd.set":
                grants = self.core.services.get("core.permission_grants")
                audit = self.core.services.get("core.audit")
                permissions = self.core.services.get("core.permissions")
                if grants is None or not hasattr(grants, "set_allow_all_cmd"):
                    raise RuntimeError("permission grant store is not available")
                if permissions is None or not hasattr(permissions, "evaluate_allow_all_cmd_grant"):
                    raise RuntimeError("permission engine is not available")
                session_id = params["session_id"]
                allowed = bool(params["allowed"])
                updated_by = str(params.get("actor", "ui"))
                decision = permissions.evaluate_allow_all_cmd_grant(
                    actor=updated_by,
                    allowed=allowed,
                )
                if decision.outcome is not PermissionOutcome.ALLOW:
                    raise PermissionError(decision.reason)
                grant = grants.set_allow_all_cmd(
                    session_id,
                    allowed,
                    updated_by=updated_by,
                )
                payload = grant.to_dict()
                if audit is not None:
                    await audit.write("permission.grant.updated", payload)
                await self.core.events.publish(
                    CoreEvent(
                        "permission.grant.updated",
                        payload,
                        correlation_id=session_id,
                    )
                )
            elif method == "providers.list":
                payload = self.core.providers.names()
            elif method == "providers.health":
                payload = await self.core.providers.health()
            elif method == "settings.conversation.get":
                payload = self.core.conversation_settings_snapshot()
            elif method == "settings.conversation.update":
                persist = bool(params.pop("persist", False))
                payload = await self.core.update_conversation_settings(
                    params,
                    persist=persist,
                )
            elif method == "settings.providers.openai_compat.get":
                payload = self.core.openai_compatible_settings_snapshot()
            elif method == "settings.providers.openai_compat.update":
                persist = bool(params.pop("persist", False))
                payload = await self.core.update_openai_compatible_settings(
                    params,
                    persist=persist,
                )
            elif method == "settings.providers.anthropic_messages.get":
                payload = self.core.anthropic_messages_settings_snapshot()
            elif method == "settings.providers.anthropic_messages.update":
                persist = bool(params.pop("persist", False))
                payload = await self.core.update_anthropic_messages_settings(
                    params,
                    persist=persist,
                )
            elif method == "settings.providers.active.get":
                payload = self.core.active_provider_settings_snapshot()
            elif method == "settings.providers.active.catalog":
                payload = await self.core.active_provider_model_catalog(params)
            elif method == "settings.providers.active.update":
                persist = bool(params.pop("persist", False))
                payload = await self.core.update_active_provider_settings(
                    params,
                    persist=persist,
                )
            elif method == "conversations.create":
                conversation = await self.core.conversations.create(
                    title=params.get("title"),
                    metadata=params.get("metadata"),
                )
                payload = conversation.to_dict()
            elif method == "conversations.list":
                conversations = await self.core.conversation_store.list(
                    limit=int(params.get("limit", 100))
                )
                payload = [conversation.to_dict() for conversation in conversations]
            elif method == "conversations.messages":
                messages = await self.core.conversation_store.messages(
                    params["conversation_id"],
                    limit=params.get("limit"),
                )
                payload = [message.to_dict() for message in messages]
            elif method == "conversations.prompt_preview":
                payload = self.core.conversations.prompt_preview(
                    str(params.get("provider_role", "chat"))
                )
            elif method == "conversations.send":
                run_id = params.get("run_id") or str(uuid4())
                message = await self.core.conversations.send(
                    params["conversation_id"],
                    params["content"],
                    provider_name=params.get("provider"),
                    provider_role=params.get("provider_role", "chat"),
                    run_id=run_id,
                    actor=params.get("actor", "ui"),
                )
                payload = {"run_id": run_id, "message": message.to_dict()}
            elif method == "conversations.cancel":
                payload = {
                    "cancelled": self.core.conversations.cancel(params["run_id"])
                }
            elif method == "desktop.state":
                payload = self.core.desktop.snapshot().to_dict()
            elif method == "desktop.attach":
                session_id = params["session_id"]
                state = await self.core.desktop.attach(
                    session_id,
                    metadata=params.get("metadata"),
                )
                payload = {"session_id": session_id, "state": state.to_dict()}
            elif method == "desktop.detach":
                state = await self.core.desktop.detach(params["session_id"])
                payload = {"state": state.to_dict()}
            elif method == "desktop.command":
                state = await self.core.desktop.handle_command(
                    params["command"],
                    value=params.get("value"),
                    source=params.get("source", "ui"),
                )
                payload = {"state": state.to_dict()}
            else:
                raise ValueError(f"Unknown method: {method}")
            return {"id": message_id, "ok": True, "result": payload}
        except Exception as exc:
            return {"id": locals().get("message_id"), "ok": False, "error": str(exc)}

    async def _write(self, response: dict[str, Any]) -> None:
        line = json.dumps(response, ensure_ascii=False, default=str)
        async with self._write_lock:
            await asyncio.to_thread(self.stdout.write, line + "\n")
            await asyncio.to_thread(self.stdout.flush)
