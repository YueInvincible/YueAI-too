from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol
from uuid import uuid4

from .contracts import (
    Capability,
    PermissionDenialCategory,
    PermissionDecision,
    PermissionOutcome,
    RiskLevel,
    ResourceScopeKind,
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


GRANT_LIFETIMES = frozenset({"once", "run", "conversation", "session"})


@dataclass(slots=True)
class SessionCapabilityGrant:
    capability: Capability
    resource: str = "*"
    allowed: bool = True
    updated_by: str = "ui"
    lifetime: str = "session"
    scope_id: str | None = None
    uses_remaining: int | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, str | bool | int | None]:
        return {
            "id": self.id,
            "capability": self.capability.value,
            "resource": self.resource,
            "allowed": self.allowed,
            "updated_by": self.updated_by,
            "lifetime": self.lifetime,
            "scope_id": self.scope_id,
            "uses_remaining": self.uses_remaining,
        }


@dataclass(slots=True)
class SessionPermissionGrant:
    session_id: str
    allow_all_cmd: bool = False
    updated_by: str = "ui"
    capability_grants: tuple[SessionCapabilityGrant, ...] = ()

    def to_dict(
        self,
    ) -> dict[str, str | bool | list[dict[str, str | bool | int | None]]]:
        return {
            "session_id": self.session_id,
            "allow_all_cmd": self.allow_all_cmd,
            "updated_by": self.updated_by,
            "capability_grants": [
                grant.to_dict() for grant in self.capability_grants
            ],
        }


class PermissionGrantStore:
    def __init__(self) -> None:
        self._session_grants: dict[str, SessionPermissionGrant] = {}

    def set_allow_all_cmd(
        self,
        session_id: str,
        allowed: bool,
        *,
        updated_by: str = "ui",
    ) -> SessionPermissionGrant:
        existing = self.get(session_id)
        grant = SessionPermissionGrant(
            session_id=session_id,
            allow_all_cmd=allowed,
            updated_by=updated_by,
            capability_grants=existing.capability_grants if existing else (),
        )
        self._session_grants[session_id] = grant
        return grant

    def set_capability_grant(
        self,
        session_id: str,
        capability: Capability | str,
        *,
        resource: str = "*",
        allowed: bool = True,
        updated_by: str = "ui",
        lifetime: str = "session",
        scope_id: str | None = None,
    ) -> SessionPermissionGrant:
        parsed_capability = (
            capability if isinstance(capability, Capability) else Capability(str(capability))
        )
        normalized_resource = str(resource or "*")
        normalized_lifetime = self._normalize_lifetime(lifetime)
        normalized_scope_id = str(scope_id) if scope_id else None
        existing = self.get(session_id)
        capability_grants = [
            grant
            for grant in (existing.capability_grants if existing else ())
            if not (
                grant.capability is parsed_capability
                and grant.resource == normalized_resource
                and grant.lifetime == normalized_lifetime
                and grant.scope_id == normalized_scope_id
            )
        ]
        capability_grants.append(
            SessionCapabilityGrant(
                capability=parsed_capability,
                resource=normalized_resource,
                allowed=allowed,
                updated_by=updated_by,
                lifetime=normalized_lifetime,
                scope_id=normalized_scope_id,
                uses_remaining=1 if normalized_lifetime == "once" and allowed else None,
            )
        )
        grant = SessionPermissionGrant(
            session_id=session_id,
            allow_all_cmd=existing.allow_all_cmd if existing else False,
            updated_by=updated_by,
            capability_grants=tuple(capability_grants),
        )
        self._session_grants[session_id] = grant
        return grant

    def revoke_capability_grant(
        self,
        session_id: str,
        *,
        grant_id: str | None = None,
        capability: Capability | str | None = None,
        resource: str | None = None,
    ) -> SessionPermissionGrant:
        existing = self.get(session_id)
        if existing is None:
            grant = SessionPermissionGrant(session_id=session_id)
            self._session_grants[session_id] = grant
            return grant
        parsed_capability = None
        if capability is not None:
            parsed_capability = (
                capability if isinstance(capability, Capability) else Capability(str(capability))
            )
        normalized_resource = str(resource) if resource is not None else None
        capability_grants = []
        for grant in existing.capability_grants:
            remove = False
            if grant_id is not None and grant.id == grant_id:
                remove = True
            elif parsed_capability is not None:
                remove = grant.capability is parsed_capability and (
                    normalized_resource is None or grant.resource == normalized_resource
                )
            if not remove:
                capability_grants.append(grant)
        updated = SessionPermissionGrant(
            session_id=session_id,
            allow_all_cmd=existing.allow_all_cmd,
            updated_by=existing.updated_by,
            capability_grants=tuple(capability_grants),
        )
        self._session_grants[session_id] = updated
        return updated

    def get(self, session_id: str | None) -> SessionPermissionGrant | None:
        if not session_id:
            return None
        return self._session_grants.get(session_id)

    def allows_shell_commands(self, session_id: str | None) -> bool:
        grant = self.get(session_id)
        return bool(grant and grant.allow_all_cmd)

    def allows_capability(
        self,
        session_id: str | None,
        capability: Capability,
        resource: str = "*",
        *,
        run_id: str | None = None,
        conversation_id: str | None = None,
    ) -> bool:
        return (
            self.match_capability_grant(
                session_id,
                capability,
                resource,
                run_id=run_id,
                conversation_id=conversation_id,
            )
            is not None
        )

    def match_capability_grant(
        self,
        session_id: str | None,
        capability: Capability,
        resource: str = "*",
        *,
        run_id: str | None = None,
        conversation_id: str | None = None,
    ) -> SessionCapabilityGrant | None:
        grant = self.get(session_id)
        if grant is None:
            return None
        normalized_resource = str(resource or "*")
        for capability_grant in grant.capability_grants:
            if capability_grant.capability is not capability or not capability_grant.allowed:
                continue
            if not self._lifetime_matches(
                capability_grant,
                session_id=session_id,
                run_id=run_id,
                conversation_id=conversation_id,
            ):
                continue
            if self._resource_matches(capability_grant.resource, normalized_resource):
                return capability_grant
        return None

    def consume_capability_grant(
        self,
        session_id: str | None,
        grant_id: str,
    ) -> None:
        existing = self.get(session_id)
        if existing is None:
            return
        capability_grants: list[SessionCapabilityGrant] = []
        for grant in existing.capability_grants:
            if grant.id != grant_id or grant.uses_remaining is None:
                capability_grants.append(grant)
                continue
            remaining = max(0, grant.uses_remaining - 1)
            if remaining > 0:
                capability_grants.append(
                    SessionCapabilityGrant(
                        id=grant.id,
                        capability=grant.capability,
                        resource=grant.resource,
                        allowed=grant.allowed,
                        updated_by=grant.updated_by,
                        lifetime=grant.lifetime,
                        scope_id=grant.scope_id,
                        uses_remaining=remaining,
                    )
                )
        self._session_grants[existing.session_id] = SessionPermissionGrant(
            session_id=existing.session_id,
            allow_all_cmd=existing.allow_all_cmd,
            updated_by=existing.updated_by,
            capability_grants=tuple(capability_grants),
        )

    @staticmethod
    def _resource_matches(grant_resource: str, requested_resource: str) -> bool:
        if grant_resource == "*":
            return True
        if grant_resource == requested_resource:
            return True
        if grant_resource.endswith("/*"):
            prefix = grant_resource[:-1]
            return requested_resource.startswith(prefix)
        return False

    @staticmethod
    def _normalize_lifetime(lifetime: str) -> str:
        normalized = str(lifetime or "session").strip().lower()
        if normalized not in GRANT_LIFETIMES:
            raise ValueError(f"Unsupported permission grant lifetime: {lifetime}")
        return normalized

    @staticmethod
    def _lifetime_matches(
        grant: SessionCapabilityGrant,
        *,
        session_id: str | None,
        run_id: str | None,
        conversation_id: str | None,
    ) -> bool:
        if grant.lifetime in {"session", "once"}:
            return True
        if grant.lifetime == "conversation":
            expected = grant.scope_id or session_id
            return expected is not None and expected in {session_id, conversation_id}
        if grant.lifetime == "run":
            return grant.scope_id is not None and grant.scope_id == run_id
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
                    "ask_user_approval",
                    "workspace_list",
                    "workspace_read",
                    "workspace_search",
                    "workspace_grep",
                    "git_status",
                    "git_diff",
                    "todo_update",
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
                    "ask_user_approval",
                    "workspace_list",
                    "workspace_read",
                    "workspace_search",
                    "workspace_grep",
                    "workspace_write",
                    "workspace_edit",
                    "workspace_ops",
                    "git_status",
                    "git_diff",
                    "todo_update",
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
                    "ask_user_approval",
                    "workspace_list",
                    "workspace_read",
                    "workspace_search",
                    "workspace_grep",
                    "workspace_write",
                    "workspace_edit",
                    "workspace_ops",
                    "git_status",
                    "git_diff",
                    "todo_update",
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
                    "shell_run",
                    "shell.session",
                    "shell_session",
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
                    "shell_run",
                    "shell.session",
                    "shell_session",
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
    MODEL_SHELL_TOOL_NAMES = frozenset(
        {"shell.exec", "shell.run", "shell_run", "shell.session", "shell_session"}
    )
    ALLOW_ALL_CMD_BLOCKED_ACTORS = frozenset({"model"})
    MODEL_SCOPE_REQUIRED_RISKS = frozenset({RiskLevel.HIGH, RiskLevel.CRITICAL})

    def __init__(
        self,
        profile: str,
        *,
        rules: list[PermissionRule] | None = None,
        approval_provider: ApprovalProvider | None = None,
        interactive_approval: bool = False,
        grant_store: PermissionGrantStore | None = None,
    ) -> None:
        if profile not in PROFILE_CAPABILITIES:
            raise ValueError(f"Unknown permission profile: {profile}")
        self.profile = profile
        self.rules = list(rules or [])
        self.approval_provider = approval_provider or DenyApprovalProvider()
        self.interactive_approval = interactive_approval
        self.grant_store = grant_store or PermissionGrantStore()

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

    def evaluate_allow_all_cmd_grant(
        self,
        *,
        actor: str,
        allowed: bool,
    ) -> PermissionDecision:
        normalized_actor = actor.strip() or "ui"
        if self.profile == "observe":
            return PermissionDecision(
                PermissionOutcome.DENY,
                "observe profile cannot change allow-all-cmd session grants",
                "session-allow-all-cmd-profile",
            )
        if normalized_actor in self.ALLOW_ALL_CMD_BLOCKED_ACTORS:
            return PermissionDecision(
                PermissionOutcome.DENY,
                "model actor cannot change allow-all-cmd session grants",
                "session-allow-all-cmd-actor",
            )
        return PermissionDecision(
            PermissionOutcome.ALLOW,
            "Non-model actor may change allow-all-cmd session grants",
            "session-allow-all-cmd-ui",
        )

    def evaluate_capability_grant(
        self,
        *,
        actor: str,
        capability: Capability | str,
        resource: str = "*",
        allowed: bool = True,
        lifetime: str = "session",
        scope_id: str | None = None,
    ) -> PermissionDecision:
        normalized_actor = actor.strip() or "ui"
        parsed_capability = (
            capability if isinstance(capability, Capability) else Capability(str(capability))
        )
        normalized_lifetime = PermissionGrantStore._normalize_lifetime(lifetime)
        if self.profile == "observe":
            return PermissionDecision(
                PermissionOutcome.DENY,
                "observe profile cannot change capability session grants",
                "session-capability-grant-profile",
            )
        if normalized_actor in self.ALLOW_ALL_CMD_BLOCKED_ACTORS:
            return PermissionDecision(
                PermissionOutcome.DENY,
                "model actor cannot change capability session grants",
                "session-capability-grant-actor",
            )
        if allowed and parsed_capability not in PROFILE_CAPABILITIES[self.profile]:
            return PermissionDecision(
                PermissionOutcome.DENY,
                f"Capability {parsed_capability.value} is outside profile {self.profile}",
                "session-capability-grant-capability",
            )
        if allowed and normalized_lifetime == "run" and not scope_id:
            return PermissionDecision(
                PermissionOutcome.DENY,
                "run lifetime grants require scope_id",
                "session-capability-grant-scope",
            )
        return PermissionDecision(
            PermissionOutcome.ALLOW,
            f"Non-model actor may change {parsed_capability.value} {normalized_lifetime} grant for {resource or '*'}",
            "session-capability-grant-ui",
        )

    async def evaluate(self, request: ToolRequest, spec: ToolSpec) -> PermissionDecision:
        resource_scope = self._request_resource_scope(request, spec)
        if (
            request.actor == "model"
            and request.tool_name in self.MODEL_SHELL_TOOL_NAMES
            and spec.capability in PROFILE_CAPABILITIES[self.profile]
            and self.grant_store.allows_shell_commands(request.session_id)
        ):
            return PermissionDecision(
                PermissionOutcome.ALLOW,
                "Session grant allow-all-cmd enabled for model shell tools",
                "session-allow-all-cmd",
            )
        capability_grant = self.grant_store.match_capability_grant(
            request.session_id,
            spec.capability,
            str(resource_scope["value"]),
            run_id=self._request_run_id(request),
            conversation_id=self._request_conversation_id(request),
        )
        if (
            request.actor == "model"
            and spec.capability in PROFILE_CAPABILITIES[self.profile]
            and capability_grant is not None
        ):
            if capability_grant.lifetime == "once":
                self.grant_store.consume_capability_grant(
                    request.session_id,
                    capability_grant.id,
                )
            return PermissionDecision(
                PermissionOutcome.ALLOW,
                "Session capability grant enabled for requested resource",
                "session-capability-grant",
                resource_scope=resource_scope,
            )
        if (
            request.actor == "model"
            and spec.capability in PROFILE_CAPABILITIES[self.profile]
            and spec.risk in self.MODEL_SCOPE_REQUIRED_RISKS
        ):
            return PermissionDecision(
                PermissionOutcome.DENY,
                "No matching scoped permission grant for model action",
                "session-capability-grant-missing",
                PermissionDenialCategory.MISSING_SCOPE,
                resource_scope,
            )
        for rule in [*self.rules, *DEFAULT_PERMISSION_RULES[self.profile]]:
            if rule.matches(request, spec):
                return await self._resolve(
                    rule.outcome,
                    request,
                    spec,
                    rule.id,
                    resource_scope,
                )

        if spec.capability not in PROFILE_CAPABILITIES[self.profile]:
            return PermissionDecision(
                PermissionOutcome.DENY,
                f"Capability {spec.capability.value} is outside profile {self.profile}",
                denial_category=PermissionDenialCategory.POLICY,
                resource_scope=resource_scope,
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
            resource_scope,
        )

    @staticmethod
    def _request_resource(request: ToolRequest) -> str:
        return str(PermissionEngine._request_resource_scope(request)["value"])

    @staticmethod
    def _request_resource_scope(
        request: ToolRequest,
        spec: ToolSpec | None = None,
    ) -> dict[str, str]:
        explicit = request.metadata.get("resource")
        if explicit:
            return {
                "kind": str(
                    request.metadata.get("resource_kind")
                    or ResourceScopeKind.GLOBAL.value
                ),
                "value": str(explicit),
                "source": "metadata.resource",
            }
        for key in ("path", "source_path", "destination_path", "from", "to"):
            value = request.arguments.get(key)
            if value:
                kind = (
                    ResourceScopeKind.WORKSPACE_PATH
                    if request.tool_name.startswith("workspace")
                    else ResourceScopeKind.FILESYSTEM_PATH
                )
                return {
                    "kind": kind.value,
                    "value": str(value),
                    "source": f"arguments.{key}",
                }
        cwd = request.arguments.get("cwd")
        if cwd:
            return {
                "kind": ResourceScopeKind.SHELL_CWD.value,
                "value": str(cwd),
                "source": "arguments.cwd",
            }
        host = request.arguments.get("host")
        if host:
            return {
                "kind": ResourceScopeKind.NETWORK_DOMAIN.value,
                "value": str(host),
                "source": "arguments.host",
            }
        url = request.arguments.get("url")
        if url:
            return {
                "kind": ResourceScopeKind.NETWORK_DOMAIN.value,
                "value": str(url),
                "source": "arguments.url",
            }
        if spec and spec.capability is Capability.SHELL_EXECUTE:
            return {
                "kind": ResourceScopeKind.SHELL_CWD.value,
                "value": "*",
                "source": "default.shell_cwd",
            }
        return {
            "kind": ResourceScopeKind.GLOBAL.value,
            "value": "*",
            "source": "default",
        }

    @staticmethod
    def _request_run_id(request: ToolRequest) -> str | None:
        value = request.metadata.get("run_id")
        return str(value) if value else None

    @staticmethod
    def _request_conversation_id(request: ToolRequest) -> str | None:
        value = request.metadata.get("conversation_id")
        return str(value) if value else None

    async def _resolve(
        self,
        outcome: PermissionOutcome,
        request: ToolRequest,
        spec: ToolSpec,
        rule_id: str | None,
        resource_scope: dict[str, str],
    ) -> PermissionDecision:
        if outcome is not PermissionOutcome.ASK:
            return PermissionDecision(
                outcome,
                "Matched permission rule",
                rule_id,
                PermissionDenialCategory.POLICY
                if outcome is PermissionOutcome.DENY
                else None,
                resource_scope,
            )
        if not self.interactive_approval:
            return PermissionDecision(
                PermissionOutcome.DENY,
                "Interactive approval is disabled",
                rule_id,
                PermissionDenialCategory.APPROVAL_UNAVAILABLE,
                resource_scope,
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
            None if approved else PermissionDenialCategory.USER,
            resource_scope,
        )

