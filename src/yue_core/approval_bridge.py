from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .audit import AuditLog
from .contracts import CoreEvent, RiskLevel, ToolRequest, ToolSpec, utc_now
from .permissions import ApprovalProvider


@dataclass(slots=True)
class PendingApproval:
    approval_id: str
    request: ToolRequest
    spec: ToolSpec
    reason: str
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    future: asyncio.Future[bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "request_id": self.request.id,
            "tool_name": self.request.tool_name,
            "actor": self.request.actor,
            "session_id": self.request.session_id,
            "reason": self.reason,
            "risk_level": self.spec.risk.value,
            "arguments": dict(self.request.arguments),
            "created_at": self.created_at,
        }


class BridgeApprovalProvider(ApprovalProvider):
    def __init__(self, publish, audit: AuditLog | None = None) -> None:
        self._publish = publish
        self._audit = audit
        self._pending: dict[str, PendingApproval] = {}
        self._lock = asyncio.Lock()

    async def request_approval(
        self,
        request: ToolRequest,
        spec: ToolSpec,
        reason: str,
    ) -> bool:
        approval_id = str(uuid4())
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        pending = PendingApproval(
            approval_id=approval_id,
            request=request,
            spec=spec,
            reason=reason,
            future=future,
        )
        async with self._lock:
            self._pending[approval_id] = pending
        payload = pending.to_dict()
        if self._audit is not None:
            await self._audit.write("approval.pending", payload)
        await self._publish(
            CoreEvent("approval.pending", payload, correlation_id=request.id)
        )
        try:
            approved = await future
        finally:
            async with self._lock:
                self._pending.pop(approval_id, None)
        resolved_payload = {
            **payload,
            "approved": approved,
        }
        if self._audit is not None:
            await self._audit.write("approval.responded", resolved_payload)
        await self._publish(
            CoreEvent("approval.responded", resolved_payload, correlation_id=request.id)
        )
        return approved

    async def list_pending(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [pending.to_dict() for pending in self._pending.values()]

    async def respond(self, approval_id: str, approved: bool) -> dict[str, Any]:
        async with self._lock:
            pending = self._pending.get(approval_id)
        if pending is None or pending.future is None:
            raise KeyError(f"Unknown approval request: {approval_id}")
        if pending.future.done():
            raise ValueError(f"Approval request already resolved: {approval_id}")
        pending.future.set_result(bool(approved))
        return {
            **pending.to_dict(),
            "approved": bool(approved),
        }

    async def shutdown(self) -> None:
        async with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for item in pending:
            if item.future is not None and not item.future.done():
                item.future.set_result(False)
