from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from .contracts import CoreEvent


class ToolActivityStore:
    def __init__(self, *, limit: int = 12) -> None:
        self._limit = limit
        self._items: list[dict[str, Any]] = []
        self._status = "No active tool run"
        self._lock = asyncio.Lock()

    async def record(self, event: CoreEvent) -> None:
        async with self._lock:
            self._apply_event(event.topic, event.payload or {})

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "items": deepcopy(self._items),
                "status": self._status,
            }

    def _apply_event(self, topic: str, payload: dict[str, Any]) -> None:
        if topic == "conversation.run.started":
            self._items = []
            self._status = "Conversation run started"
            return

        current = list(self._items)
        if topic == "conversation.tool.requested":
            tool_call = payload.get("tool_call") or {}
            self._upsert_front(
                {
                    "run_id": payload.get("run_id"),
                    "conversation_id": payload.get("conversation_id"),
                    "tool_call_id": tool_call.get("id"),
                    "request_id": payload.get("request_id"),
                    "tool_name": tool_call.get("name") or "unknown tool",
                    "arguments": deepcopy(tool_call.get("arguments") or {}),
                    "status": "requested",
                    "output": None,
                    "error": None,
                    "approval_id": None,
                }
            )
            self._status = f"Requested {tool_call.get('name') or 'tool'}"
            return

        if topic == "tool.started":
            item = self._find_or_create(
                request_id=payload.get("request_id"),
                tool_call_id=payload.get("tool_call_id"),
                fallback_tool_name=payload.get("tool"),
            )
            item["request_id"] = payload.get("request_id") or item.get("request_id")
            item["run_id"] = payload.get("run_id") or item.get("run_id")
            item["conversation_id"] = payload.get("conversation_id") or item.get("conversation_id")
            item["tool_call_id"] = payload.get("tool_call_id") or item.get("tool_call_id")
            item["status"] = "running"
            self._status = f"Running {payload.get('tool') or 'tool'}"
            return

        if topic == "approval.pending":
            item = self._find_or_create(
                request_id=payload.get("request_id"),
                tool_call_id=None,
                fallback_tool_name=payload.get("tool_name"),
            )
            item["request_id"] = payload.get("request_id") or item.get("request_id")
            item["approval_id"] = payload.get("approval_id") or item.get("approval_id")
            item["arguments"] = deepcopy(payload.get("arguments") or item.get("arguments") or {})
            item["error"] = payload.get("reason") or item.get("error")
            item["status"] = "waiting_approval"
            self._status = f"Approval requested for {payload.get('tool_name') or 'tool'}"
            return

        if topic == "approval.responded":
            item = self._find_or_create(
                request_id=payload.get("request_id"),
                tool_call_id=None,
                fallback_tool_name=payload.get("tool_name"),
                approval_id=payload.get("approval_id"),
            )
            item["request_id"] = payload.get("request_id") or item.get("request_id")
            item["approval_id"] = payload.get("approval_id") or item.get("approval_id")
            approved = bool(payload.get("approved"))
            item["status"] = "approved_pending_run" if approved else "denied_by_user"
            item["error"] = None if approved else "Denied by user approval"
            self._status = (
                f"Approved {payload.get('tool_name') or 'tool'}"
                if approved
                else f"Denied {payload.get('tool_name') or 'tool'}"
            )
            return

        if topic == "tool.finished":
            item = self._find_or_create(
                request_id=payload.get("request_id"),
                tool_call_id=payload.get("tool_call_id"),
                fallback_tool_name=payload.get("tool_name") or payload.get("tool"),
            )
            item["request_id"] = payload.get("request_id") or item.get("request_id")
            item["tool_call_id"] = payload.get("tool_call_id") or item.get("tool_call_id")
            item["run_id"] = payload.get("run_id") or item.get("run_id")
            item["conversation_id"] = payload.get("conversation_id") or item.get("conversation_id")
            item["status"] = (
                self._classify_denied_status(item, payload)
                if payload.get("status") == "denied"
                else payload.get("status") or item.get("status")
            )
            if "output" in payload:
                item["output"] = deepcopy(payload.get("output"))
            item["error"] = payload.get("error") or item.get("error")
            self._status = (
                f"{payload.get('tool_name') or payload.get('tool') or 'Tool'} "
                f"{payload.get('status') or 'finished'}"
            )
            return

        if topic == "conversation.tool.completed":
            item = self._find_or_create(
                request_id=None,
                tool_call_id=payload.get("tool_call_id"),
                fallback_tool_name=payload.get("tool"),
            )
            item["tool_call_id"] = payload.get("tool_call_id") or item.get("tool_call_id")
            item["run_id"] = payload.get("run_id") or item.get("run_id")
            item["conversation_id"] = payload.get("conversation_id") or item.get("conversation_id")
            item["status"] = payload.get("status") or item.get("status")
            self._status = f"{payload.get('tool') or 'Tool'} {payload.get('status') or 'completed'}"
            return

        if topic == "conversation.run.failed":
            self._status = f"Conversation run failed: {payload.get('error') or 'unknown error'}"
            return

        if topic == "conversation.run.completed" and current:
            self._status = "Conversation run completed"

    def _find_or_create(
        self,
        *,
        request_id: str | None,
        tool_call_id: str | None,
        fallback_tool_name: str | None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        for item in self._items:
            if request_id and item.get("request_id") == request_id:
                return item
            if tool_call_id and item.get("tool_call_id") == tool_call_id:
                return item
            if approval_id and item.get("approval_id") == approval_id:
                return item
        created = {
            "run_id": None,
            "conversation_id": None,
            "tool_call_id": tool_call_id,
            "request_id": request_id,
            "tool_name": fallback_tool_name or "unknown tool",
            "arguments": {},
            "status": "requested",
            "output": None,
            "error": None,
            "approval_id": approval_id,
        }
        self._upsert_front(created)
        return self._items[0]

    def _upsert_front(self, item: dict[str, Any]) -> None:
        request_id = item.get("request_id")
        tool_call_id = item.get("tool_call_id")
        approval_id = item.get("approval_id")
        self._items = [
            existing
            for existing in self._items
            if not (
                (request_id and existing.get("request_id") == request_id)
                or (tool_call_id and existing.get("tool_call_id") == tool_call_id)
                or (approval_id and existing.get("approval_id") == approval_id)
            )
        ]
        self._items = [item, *self._items][: self._limit]

    @staticmethod
    def _classify_denied_status(item: dict[str, Any], payload: dict[str, Any]) -> str:
        permission = (payload.get("metadata") or {}).get("permission") or {}
        category = permission.get("denial_category")
        if category == "denied_by_user":
            return "denied_by_user"
        if category == "denied_by_missing_scope":
            return "denied_by_missing_scope"
        if category == "denied_by_approval_unavailable":
            return "denied_by_approval_unavailable"
        if category == "denied_by_policy":
            return "denied_by_policy"
        error = str(payload.get("error") or item.get("error") or "").lower()
        if item.get("approval_id") or "user denied" in error:
            return "denied_by_user"
        return "denied_by_profile"
