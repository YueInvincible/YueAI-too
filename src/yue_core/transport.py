from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, TextIO
from uuid import uuid4

from .app import YueCore
from .contracts import CoreEvent


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
                payload = [
                    {
                        "name": spec.name,
                        "description": spec.description,
                        "input_schema": spec.input_schema,
                        "capability": spec.capability.value,
                        "risk": spec.risk.value,
                        "plugin_id": spec.plugin_id,
                    }
                    for spec in self.core.registry.list_specs()
                ]
            elif method == "tools.invoke":
                result = await self.core.invoke(
                    params["name"],
                    params.get("arguments", {}),
                    actor=params.get("actor", "ui"),
                    session_id=params.get("session_id"),
                )
                payload = result.to_dict()
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
