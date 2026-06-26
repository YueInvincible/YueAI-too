from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from .contracts import (
    Capability,
    PermissionDecision,
    PermissionOutcome,
    RiskLevel,
    ToolRequest,
    ToolSpec,
)


class ApprovalProvider(Protocol):
    async def request_approval(
        self,
        request: ToolRequest,
        spec: ToolSpec,
        reason: str,
    ) -> bool: ...


class DenyApprovalProvider:
    async def request_approval(
        self,
        request: ToolRequest,
        spec: ToolSpec,
        reason: str,
    ) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class PermissionRule:
    id: str
    outcome: PermissionOutcome
    capabilities: frozenset[Capability] | None = None
    tools: frozenset[str] | None = None
    maximum_risk: RiskLevel | None = None
    actors: frozenset[str] | None = None

    def matches(self, request: ToolRequest, spec: ToolSpec) -> bool:
        if self.capabilities is not None and spec.capability not in self.capabilities:
            return False
        if self.tools is not None and spec.name not in self.tools:
            return False
        if self.actors is not None and request.actor not in self.actors:
            return False
        if self.maximum_risk is not None:
            order = list(RiskLevel)
            if order.index(spec.risk) > order.index(self.maximum_risk):
                return False
        return True


PROFILE_CAPABILITIES: dict[str, frozenset[Capability]] = {
    "observe": frozenset(
        {
            Capability.CORE_READ,
            Capability.FILE_READ,
            Capability.PROCESS_READ,
        }
    ),
    "assist": frozenset(
        {
            Capability.CORE_READ,
            Capability.FILE_READ,
            Capability.FILE_WRITE,
            Capability.PROCESS_READ,
            Capability.SHELL_EXECUTE,
            Capability.NETWORK_ACCESS,
        }
    ),
    "admin": frozenset(Capability),
}


DEFAULT_PERMISSION_RULES: dict[str, list[PermissionRule]] = {
    "observe": [
        PermissionRule(
            id="observe-readonly",
            outcome=PermissionOutcome.ALLOW,
            tools=frozenset(
                {
                    "core.echo",
                    "core.health",
                    "approval.request",
                    "file.read",
                    "file.list",
                    "file.search",
                    "workspace.list",
                    "workspace.read",
                    "workspace.search",
                    "workspace.grep",
                    "todo.update",
                    "process.list",
                    "git.status",
                    "git.diff",
                }
            ),
        ),
    ],
    "assist": [
        PermissionRule(
            id="assist-read-and-edit-user",
            outcome=PermissionOutcome.ALLOW,
            tools=frozenset(
                {
                    "core.echo",
                    "core.health",
                    "approval.request",
                    "file.read",
                    "file.list",
                    "file.search",
                    "file.write",
                    "file.edit",
                    "file.move",
                    "workspace.list",
                    "workspace.read",
                    "workspace.search",
                    "workspace.grep",
                    "workspace.write",
                    "workspace.edit",
                    "workspace.ops",
                    "todo.update",
                    "process.list",
                    "git.status",
                    "git.diff",
                }
            ),
            actors=frozenset({"user", "ui", "system"}),
        ),
        PermissionRule(
            id="assist-read-and-edit-model",
            outcome=PermissionOutcome.ALLOW,
            tools=frozenset(
                {
                    "core.echo",
                    "core.health",
                    "approval.request",
                    "file.read",
                    "file.list",
                    "file.search",
                    "file.write",
                    "file.edit",
                    "file.move",
                    "workspace.list",
                    "workspace.read",
                    "workspace.search",
                    "workspace.grep",
                    "workspace.write",
                    "workspace.edit",
                    "workspace.ops",
                    "todo.update",
                    "process.list",
                    "git.status",
                    "git.diff",
                }
            ),
            actors=frozenset({"model"}),
        ),
        PermissionRule(
            id="assist-dangerous-actions-user",
            outcome=PermissionOutcome.ASK,
            tools=frozenset(
                {
                    "file.delete",
                    "shell.exec",
                    "shell.run",
                    "shell.session",
                    "process.kill",
                    "package.install",
                }
            ),
            actors=frozenset({"user", "ui", "system"}),
        ),
        PermissionRule(
            id="assist-dangerous-actions-model",
            outcome=PermissionOutcome.DENY,
            tools=frozenset(
                {
                    "file.delete",
                    "shell.exec",
                    "shell.run",
                    "shell.session",
                    "process.kill",
                    "package.install",
                }
            ),
            actors=frozenset({"model"}),
        ),
    ],
    "admin": [],
}


class PermissionEngine:
    def __init__(
        self,
        profile: str,
        *,
        rules: list[PermissionRule] | None = None,
        approval_provider: ApprovalProvider | None = None,
        interactive_approval: bool = False,
    ) -> None:
        if profile not in PROFILE_CAPABILITIES:
            raise ValueError(f"Unknown permission profile: {profile}")
        self.profile = profile
        self.rules = list(rules or [])
        self.approval_provider = approval_provider or DenyApprovalProvider()
        self.interactive_approval = interactive_approval

    async def request_explicit_approval(
        self,
        action_description: str,
        risk_level: str | RiskLevel,
        *,
        actor: str = "model",
        session_id: str | None = None,
    ) -> PermissionDecision:
        if not self.interactive_approval:
            return PermissionDecision(
                PermissionOutcome.DENY,
                "Interactive approval is disabled",
                "explicit-approval",
            )
        risk = risk_level if isinstance(risk_level, RiskLevel) else RiskLevel(str(risk_level))
        request = ToolRequest(
            "approval.request",
            {
                "action_description": action_description,
                "risk_level": risk.value,
            },
            actor=actor,
            session_id=session_id,
        )
        spec = ToolSpec(
            "approval.request",
            "Request explicit user approval for a proposed action.",
            {
                "type": "object",
                "properties": {
                    "action_description": {"type": "string"},
                    "risk_level": {"type": "string"},
                },
                "required": ["action_description", "risk_level"],
                "additionalProperties": False,
            },
            Capability.CORE_READ,
            risk,
        )
        approved = await self.approval_provider.request_approval(
            request,
            spec,
            action_description,
        )
        return PermissionDecision(
            PermissionOutcome.ALLOW if approved else PermissionOutcome.DENY,
            "User approved action" if approved else "User denied action",
            "explicit-approval",
        )

    async def evaluate(self, request: ToolRequest, spec: ToolSpec) -> PermissionDecision:
        for rule in [*self.rules, *DEFAULT_PERMISSION_RULES[self.profile]]:
            if rule.matches(request, spec):
                return await self._resolve(rule.outcome, request, spec, rule.id)

        if spec.capability not in PROFILE_CAPABILITIES[self.profile]:
            return PermissionDecision(
                PermissionOutcome.DENY,
                f"Capability {spec.capability.value} is outside profile {self.profile}",
            )

        if self.profile == "admin":
            return PermissionDecision(
                PermissionOutcome.ALLOW,
                "Admin profile allows all registered capabilities",
            )

        if spec.risk is RiskLevel.LOW:
            return PermissionDecision(
                PermissionOutcome.ALLOW,
                "Low-risk tool allowed by active profile",
            )

        return await self._resolve(
            PermissionOutcome.ASK,
            request,
            spec,
            None,
        )

    async def _resolve(
        self,
        outcome: PermissionOutcome,
        request: ToolRequest,
        spec: ToolSpec,
        rule_id: str | None,
    ) -> PermissionDecision:
        if outcome is not PermissionOutcome.ASK:
            return PermissionDecision(outcome, "Matched permission rule", rule_id)
        if not self.interactive_approval:
            return PermissionDecision(
                PermissionOutcome.DENY,
                "Interactive approval is disabled",
                rule_id,
            )
        approved = await self.approval_provider.request_approval(
            request,
            spec,
            "Tool requires explicit approval",
        )
        return PermissionDecision(
            PermissionOutcome.ALLOW if approved else PermissionOutcome.DENY,
            "User approved tool" if approved else "User denied tool",
            rule_id,
        )

