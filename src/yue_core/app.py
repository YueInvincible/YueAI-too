from __future__ import annotations

import copy
import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .audit import AuditLog
from .builtin_tools import (
    ApprovalRequestTool,
    AskUserApprovalTool,
    EchoTool,
    FileDeleteTool,
    FileEditTool,
    FileListTool,
    FileMoveTool,
    FileReadTool,
    FileSearchTool,
    FileWriteTool,
    GitDiffTool,
    GitStatusTool,
    HealthTool,
    PackageInstallTool,
    ProcessKillTool,
    ProcessListTool,
    ShellExecTool,
    ShellSessionTool,
    ShellRunTool,
    TodoUpdateTool,
    WorkspaceEditTool,
    WorkspaceGrepTool,
    WorkspaceListTool,
    WorkspaceOpsTool,
    WorkspaceReadTool,
    WorkspaceSearchTool,
    WorkspaceWriteTool,
)
from .config import DEFAULTS, Settings, load_settings, save_settings
from .conversation import (
    ConversationOrchestrator,
    InMemoryConversationStore,
    SQLiteConversationStore,
)
from .contracts import CoreEvent, Tool, ToolContext, ToolRequest, ToolResult, ToolSpec
from .desktop import DesktopSessionManager
from .events import EventBus
from .fake_provider import EchoModelProvider
from .permissions import ApprovalProvider, PermissionEngine
from .permissions import PermissionGrantStore
from .plugins import PluginManager
from .providers import ModelProviderRegistry
from .services import ServiceRegistry
from .shell_sessions import ShellSessionManager
from .tools import ToolExecutor, ToolRegistry
from .version import VERSION
from .openai_compat import (
    OpenAICompatibleProvider,
    coerce_provider_configs,
    default_base_url as default_openai_base_url,
    normalize_provider_config,
)
from .anthropic import (
    AnthropicMessagesProvider,
    coerce_provider_configs as coerce_anthropic_provider_configs,
    default_base_url as default_anthropic_base_url,
    normalize_provider_config as normalize_anthropic_provider_config,
)
from .approval_bridge import BridgeApprovalProvider
from .tool_activity import ToolActivityStore
from .tool_catalog import filter_tool_specs_for_role
from .tool_guidance import build_tool_guide

LOGGER = logging.getLogger(__name__)

CODING_AGENT_TOOL_ALIASES: dict[str, str] = {
    "workspace.list": "workspace_list",
    "workspace.read": "workspace_read",
    "workspace.search": "workspace_search",
    "workspace.grep": "workspace_grep",
    "workspace.write": "workspace_write",
    "workspace.edit": "workspace_edit",
    "workspace.ops": "workspace_ops",
    "shell.run": "shell_run",
    "shell.session": "shell_session",
    "git.status": "git_status",
    "git.diff": "git_diff",
    "todo.update": "todo_update",
}

ACTIVE_PROVIDER_OPTIONS: tuple[dict[str, Any], ...] = (
    {
        "kind": "llama.cpp",
        "label": "Local llama.cpp",
        "family": "local",
        "plugin_id": "llama.cpp",
        "default_provider_name": "localhost.chat",
        "default_host": "127.0.0.1",
        "default_port": 8080,
        "default_api_key_env": "",
    },
    {
        "kind": "ollama",
        "label": "Ollama",
        "family": "local",
        "plugin_id": "openai.compat",
        "default_provider_name": "ollama.chat",
        "default_host": "127.0.0.1",
        "default_port": 11434,
        "default_api_key_env": "",
    },
    {
        "kind": "lmstudio",
        "label": "LM Studio",
        "family": "local",
        "plugin_id": "openai.compat",
        "default_provider_name": "lmstudio.chat",
        "default_host": "127.0.0.1",
        "default_port": 1234,
        "default_api_key_env": "",
    },
    {
        "kind": "custom",
        "label": "Custom OpenAI-compatible",
        "family": "local",
        "plugin_id": "openai.compat",
        "default_provider_name": "custom.chat",
        "default_host": "127.0.0.1",
        "default_port": 8080,
        "default_api_key_env": "",
    },
    {
        "kind": "openai",
        "label": "OpenAI",
        "family": "cloud",
        "plugin_id": "openai.compat",
        "default_provider_name": "openai.chat",
        "default_host": "",
        "default_port": 443,
        "default_api_key_env": "OPENAI_API_KEY",
    },
    {
        "kind": "google",
        "label": "Google AI",
        "family": "cloud",
        "plugin_id": "openai.compat",
        "default_provider_name": "google.chat",
        "default_host": "",
        "default_port": 443,
        "default_api_key_env": "GEMINI_API_KEY",
    },
    {
        "kind": "openrouter",
        "label": "OpenRouter",
        "family": "cloud",
        "plugin_id": "openai.compat",
        "default_provider_name": "openrouter.chat",
        "default_host": "",
        "default_port": 443,
        "default_api_key_env": "OPENROUTER_API_KEY",
    },
    {
        "kind": "anthropic",
        "label": "Anthropic",
        "family": "cloud",
        "plugin_id": "anthropic.messages",
        "default_provider_name": "anthropic.chat",
        "default_host": "",
        "default_port": 443,
        "default_api_key_env": "ANTHROPIC_API_KEY",
    },
)

ACTIVE_PROVIDER_BY_KIND = {
    str(item["kind"]): item for item in ACTIVE_PROVIDER_OPTIONS
}


class ToolAlias:
    def __init__(self, target: Tool, alias_name: str) -> None:
        self._target = target
        self.spec = replace(
            target.spec,
            name=alias_name,
            metadata={
                **dict(target.spec.metadata),
                "alias_of": target.spec.name,
            },
        )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        return await self._target.invoke(arguments, context)


class YueCore:
    def __init__(
        self,
        settings: Settings,
        *,
        approval_provider: ApprovalProvider | None = None,
    ) -> None:
        self.settings = settings
        self.events = EventBus()
        self.registry = ToolRegistry()
        self.providers = ModelProviderRegistry()
        self.audit = AuditLog(settings.core.data_dir / "audit.jsonl")
        self.services = ServiceRegistry()
        self.workspace_root = Path.cwd().resolve()
        self.todo_state: dict[str, list[dict[str, Any]]] = {}
        self.shell_sessions = ShellSessionManager()
        self.permission_grants = PermissionGrantStore()
        self.tool_activity = ToolActivityStore()
        self.approvals = (
            approval_provider
            if approval_provider is not None
            else BridgeApprovalProvider(self.events.publish, self.audit)
        )
        self.services.register("core.events", self.events, owner="core")
        self.services.register("core.audit", self.audit, owner="core")
        self.services.register("core.settings", settings, owner="core")
        self.services.register("core.workspace_root", self.workspace_root, owner="core")
        self.services.register("core.todo_state", self.todo_state, owner="core")
        self.services.register("core.shell_sessions", self.shell_sessions, owner="core")
        self.services.register("core.permission_grants", self.permission_grants, owner="core")
        self.services.register("core.tool_activity", self.tool_activity, owner="core")
        self.services.register("core.approvals", self.approvals, owner="core")
        self._event_unsubscribes = self._subscribe_tool_activity()
        self.desktop = DesktopSessionManager(
            self.events.publish,
            hotkey=settings.desktop.hotkey,
            model_path=settings.desktop.model_path,
            window_anchor=settings.desktop.window_anchor,
            click_opens_console=settings.desktop.click_opens_console,
        )
        self.services.register("desktop.session", self.desktop, owner="core")
        self.permissions = PermissionEngine(
            settings.permissions.profile,
            approval_provider=self.approvals,
            interactive_approval=settings.permissions.interactive_approval,
            grant_store=self.permission_grants,
        )
        self.services.register("core.permissions", self.permissions, owner="core")
        self.executor = ToolExecutor(
            self.registry,
            self.permissions,
            self.events,
            self.audit,
            default_timeout_seconds=settings.core.tool_timeout_seconds,
            services=self.services,
        )
        sqlite_path = settings.conversation.sqlite_path
        if not sqlite_path.is_absolute():
            sqlite_path = settings.core.data_dir / sqlite_path
        self.conversation_store = (
            SQLiteConversationStore(sqlite_path)
            if settings.conversation.store_backend == "sqlite"
            else InMemoryConversationStore()
        )
        conversation_routes = self._normalize_conversation_routes(settings)
        self.conversations = ConversationOrchestrator(
            self.conversation_store,
            self.providers,
            self.registry,
            self.executor,
            self.events,
            self.audit,
            default_provider=settings.conversation.default_provider,
            routes=conversation_routes,
            prompt_profiles=settings.conversation.prompt_profiles,
            max_tool_iterations=settings.conversation.max_tool_iterations,
            max_tool_output_chars=settings.conversation.max_tool_output_chars,
        )
        self.services.register(
            "conversation.store", self.conversation_store, owner="core"
        )
        self.services.register(
            "conversation.orchestrator", self.conversations, owner="core"
        )
        self.plugins = PluginManager(
            settings.plugins.roots,
            settings.plugins.enabled,
            self.registry,
            self.events,
            self.services,
            self.providers,
            settings.plugins.options,
        )
        self._started = False

    @staticmethod
    def _normalize_conversation_routes(settings: Settings) -> dict[str, dict[str, str]]:
        routes = {
            str(role): dict(route) for role, route in settings.conversation.routes.items()
        }
        default_routes = DEFAULTS["conversation"]["routes"]
        for role in ("chat", "coding_agent"):
            route = routes.setdefault(role, dict(default_routes[role]))
            default_route = default_routes[role]
            if (
                route.get("provider") == default_route["provider"]
                and settings.conversation.default_provider != default_route["provider"]
            ):
                route["provider"] = settings.conversation.default_provider
        return routes

    @classmethod
    def from_path(cls, path: Path | None = None) -> "YueCore":
        return cls(load_settings(path))

    def _subscribe_tool_activity(self) -> list[Any]:
        return [
            self.events.subscribe("conversation.*", self.tool_activity.record),
            self.events.subscribe("approval.*", self.tool_activity.record),
            self.events.subscribe("tool.*", self.tool_activity.record),
        ]

    def conversation_settings_snapshot(self) -> dict[str, Any]:
        return {
            "default_provider": self.settings.conversation.default_provider,
            "routes": {
                str(role): dict(route)
                for role, route in self.conversations.routes.items()
            },
            "prompt_profiles": {
                str(name): dict(profile)
                for name, profile in self.conversations.prompt_profiles.items()
            },
        }

    def agent_bundle_snapshot(self, provider_role: str = "coding_agent") -> dict[str, Any]:
        route = dict(self.conversations.routes.get(provider_role) or {})
        prompt_preview = self.conversations.prompt_preview(provider_role)
        tool_specs = filter_tool_specs_for_role(self.registry.list_specs(), provider_role)
        tool_guide = build_tool_guide(tool_specs, provider_role=provider_role)
        tool_rules = [
            {
                "name": item["name"],
                "when_to_use": item["when_to_use"],
                "avoid_when": item["avoid_when"],
                "parallel_safe": item["parallel_safe"],
                "mutates_state": item["mutates_state"],
                "risk": item["risk"],
            }
            for item in tool_guide["tools"]
        ]
        codex_manifest = {
            "provider_role": provider_role,
            "system_prompt": prompt_preview["system_instruction"],
            "tool_instructions": tool_guide["workflow"],
            "approval_rules": {
                "profile": self.settings.permissions.profile,
                "interactive_approval": self.settings.permissions.interactive_approval,
                "dangerous_model_actions_blocked_in_assist": True,
            },
            "parallel_rules": {
                "read_only_parallel_only": True,
                "writes_and_shell_sequential": True,
            },
            "tools": tool_rules,
        }
        return {
            "provider_role": provider_role,
            "default_provider": self.settings.conversation.default_provider,
            "route": {
                "provider": str(route.get("provider") or self.settings.conversation.default_provider),
                "prompt_profile": self.conversations.resolve_prompt_profile(provider_role),
            },
            "active_provider": self._resolve_active_provider_details(),
            "prompt_preview": prompt_preview,
            "tool_guide": tool_guide,
            "codex_manifest": codex_manifest,
            "tools": [
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
                for spec in tool_specs
            ],
        }

    def agent_starter_pack(self, provider_role: str = "coding_agent") -> dict[str, Any]:
        bundle = self.agent_bundle_snapshot(provider_role)
        codex_manifest = copy.deepcopy(bundle["codex_manifest"])
        tool_manifest_json = json.dumps(codex_manifest, indent=2, ensure_ascii=False)
        integration_checklist = [
            "Load the system prompt exactly as provided before the first user turn.",
            "Register tools with the exact filtered names from the manifest.",
            "Treat read-only tools as the only safe parallel batch; keep writes and shell actions sequential.",
            "Preserve approval boundaries from the manifest before any risky action.",
            "Prefer inspect -> edit -> verify, and ask the user when intent or blast radius is unclear.",
        ]
        starter_prompt = (
            "You are a coding agent attached to the YueAI runtime.\n"
            "Follow the system prompt and tool manifest below.\n"
            "Do not rename tools, widen permissions, or parallelize state-changing actions.\n"
            "When uncertain, inspect first and ask the user before destructive or ambiguous steps."
        )
        text = "\n".join(
            [
                f"# YueAI {provider_role} starter pack",
                "",
                "Use this pack when wiring another agent client to the YueAI runtime.",
                "",
                "## Starter prompt",
                "```text",
                starter_prompt,
                "```",
                "",
                "## Runtime system prompt",
                "```text",
                bundle["prompt_preview"]["system_instruction"],
                "```",
                "",
                "## Integration checklist",
                *[f"- {item}" for item in integration_checklist],
                "",
                "## Codex-style tool manifest",
                "```json",
                tool_manifest_json,
                "```",
            ]
        )
        return {
            "provider_role": provider_role,
            "name": f"YueAI {provider_role} starter pack",
            "summary": "Copy-ready prompt and tool rules for wiring another coding-agent client.",
            "starter_prompt": starter_prompt,
            "system_prompt": bundle["prompt_preview"]["system_instruction"],
            "codex_manifest": codex_manifest,
            "tool_manifest_json": tool_manifest_json,
            "integration_checklist": integration_checklist,
            "text": text,
        }

    def openai_compatible_settings_snapshot(self) -> dict[str, Any]:
        config = self.settings.plugins.options.get("openai.compat", {})
        providers = [
            normalize_provider_config(item)
            for item in coerce_provider_configs(config)
        ] if config else []
        return {"providers": providers}

    def anthropic_messages_settings_snapshot(self) -> dict[str, Any]:
        config = self.settings.plugins.options.get("anthropic.messages", {})
        providers = [
            normalize_anthropic_provider_config(item)
            for item in coerce_anthropic_provider_configs(config)
        ] if config else []
        return {"providers": providers}

    @staticmethod
    def _active_provider_option(kind: str) -> dict[str, Any]:
        option = ACTIVE_PROVIDER_BY_KIND.get(kind)
        if option is None:
            raise ValueError(f"Unsupported provider kind: {kind}")
        return copy.deepcopy(option)

    @staticmethod
    def _provider_port_from_base_url(base_url: str, fallback: int) -> int:
        parsed = urlsplit(base_url)
        return int(parsed.port or fallback)

    @staticmethod
    def _provider_host_from_base_url(base_url: str, fallback: str) -> str:
        parsed = urlsplit(base_url)
        return str(parsed.hostname or fallback)

    def _provider_details_from_kind(
        self,
        kind: str,
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        option = self._active_provider_option(kind)
        base_url = str(
            config.get("base_url")
            or (
                default_anthropic_base_url(kind)
                if kind == "anthropic"
                else default_openai_base_url(kind)
            )
        ).rstrip("/")
        details: dict[str, Any] = {
            "kind": kind,
            "label": option["label"],
            "family": option["family"],
            "plugin_id": option["plugin_id"],
            "provider_name": str(
                config.get("provider_name") or option["default_provider_name"]
            ).strip(),
            "backend": str(config.get("backend") or kind).strip().lower(),
            "base_url": base_url,
            "host": self._provider_host_from_base_url(
                base_url, str(option.get("default_host", ""))
            ),
            "port": self._provider_port_from_base_url(
                base_url, int(option.get("default_port", 0) or 0)
            ),
            "model": str(config.get("model", "")).strip(),
            "api_key_env": str(
                config.get("api_key_env") or option.get("default_api_key_env", "")
            ).strip(),
            "timeout_seconds": float(config.get("timeout_seconds", 120.0)),
            "health_timeout_seconds": float(
                config.get("health_timeout_seconds", 5.0)
            ),
            "temperature": float(config.get("temperature", 0.7)),
            "max_tokens": int(config.get("max_tokens", 1024)),
            "headers": dict(config.get("headers", {})),
        }
        if kind == "anthropic":
            details["anthropic_version"] = str(
                config.get("anthropic_version", "2023-06-01")
            ).strip()
        return details

    def _resolve_active_provider_details(self) -> dict[str, Any]:
        provider_name = str(self.settings.conversation.default_provider).strip()

        llama_config = self.settings.plugins.options.get("llama.cpp", {})
        if (
            isinstance(llama_config, Mapping)
            and str(llama_config.get("provider_name", "")).strip() == provider_name
        ):
            details = self._provider_details_from_kind("llama.cpp", llama_config)
            details["selected"] = True
            return details

        for item in self.openai_compatible_settings_snapshot()["providers"]:
            if str(item.get("provider_name", "")).strip() == provider_name:
                details = self._provider_details_from_kind(
                    str(item.get("backend", "custom")).strip().lower(),
                    item,
                )
                details["selected"] = True
                return details

        for item in self.anthropic_messages_settings_snapshot()["providers"]:
            if str(item.get("provider_name", "")).strip() == provider_name:
                details = self._provider_details_from_kind("anthropic", item)
                details["selected"] = True
                return details

        return {
            "kind": "fake.echo",
            "label": "Built-in echo",
            "family": "builtin",
            "plugin_id": "core",
            "provider_name": provider_name or "fake.echo",
            "backend": "fake",
            "base_url": "",
            "host": "",
            "port": 0,
            "model": "echo",
            "api_key_env": "",
            "timeout_seconds": 30.0,
            "health_timeout_seconds": 5.0,
            "temperature": 0.0,
            "max_tokens": 256,
            "headers": {},
            "selected": True,
        }

    def active_provider_settings_snapshot(self) -> dict[str, Any]:
        return {
            "single_provider_mode": True,
            "active_provider": self._resolve_active_provider_details(),
            "provider_options": [copy.deepcopy(item) for item in ACTIVE_PROVIDER_OPTIONS],
            "conversation": self.conversation_settings_snapshot(),
        }

    def _normalize_active_provider_payload(
        self,
        payload: Mapping[str, Any],
        *,
        require_model: bool = True,
    ) -> dict[str, Any]:
        kind = str(payload.get("kind") or payload.get("backend") or "").strip().lower()
        option = self._active_provider_option(kind)
        provider_name = str(
            payload.get("provider_name") or option["default_provider_name"]
        ).strip()
        if not provider_name:
            raise ValueError("provider_name must not be empty")

        base_url = str(payload.get("base_url", "")).strip().rstrip("/")
        host = str(payload.get("host", "")).strip()
        port_raw = payload.get("port", option.get("default_port", 0))
        try:
            port = int(port_raw or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("port must be a valid integer") from exc
        if option["family"] == "local":
            if not host:
                host = str(option.get("default_host", "")).strip()
            if port <= 0:
                port = int(option.get("default_port", 0) or 0)
        if not base_url:
            if kind == "anthropic":
                base_url = default_anthropic_base_url(kind).rstrip("/")
            elif option["family"] == "local":
                if not host or port <= 0:
                    raise ValueError("host and port are required for local providers")
                suffix = "" if kind == "llama.cpp" else "/v1"
                base_url = f"http://{host}:{port}{suffix}"
            else:
                base_url = default_openai_base_url(kind).rstrip("/")

        model = str(payload.get("model", "")).strip()
        if require_model and not model:
            raise ValueError("model must not be empty")

        config: dict[str, Any] = {
            "kind": kind,
            "provider_name": provider_name,
            "backend": "anthropic" if kind == "anthropic" else kind,
            "base_url": base_url,
            "model": model,
            "api_key_env": str(
                payload.get("api_key_env") or option.get("default_api_key_env", "")
            ).strip(),
            "timeout_seconds": float(payload.get("timeout_seconds", 120.0)),
            "health_timeout_seconds": float(payload.get("health_timeout_seconds", 5.0)),
            "temperature": float(payload.get("temperature", 0.7)),
            "max_tokens": int(payload.get("max_tokens", 1024)),
            "headers": dict(payload.get("headers", {})),
        }
        if kind == "anthropic":
            config["anthropic_version"] = str(
                payload.get("anthropic_version", "2023-06-01")
            ).strip() or "2023-06-01"
        return config

    async def active_provider_model_catalog(
        self,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if payload is None:
            provider = self._normalize_active_provider_payload(
                self._resolve_active_provider_details(),
                require_model=False,
            )
        else:
            raw_provider = payload.get("provider", payload)
            if not isinstance(raw_provider, Mapping):
                raise ValueError("provider must be an object")
            provider = self._normalize_active_provider_payload(
                raw_provider,
                require_model=False,
            )

        model = str(provider.get("model", "")).strip()
        probe_config = copy.deepcopy(provider)
        probe_config["model"] = model or "__catalog_probe__"

        try:
            if provider["kind"] == "anthropic":
                health = await AnthropicMessagesProvider(probe_config).health()
            else:
                health = await OpenAICompatibleProvider(probe_config).health()
        except Exception as exc:
            health = {
                "provider": provider["provider_name"],
                "backend": provider["backend"],
                "base_url": provider["base_url"],
                "model": model,
                "ok": False,
                "reachable": False,
                "error": str(exc),
                "models": [],
            }

        models = [str(item) for item in health.get("models", []) if str(item).strip()]
        selected_model = model or (models[0] if models else "")
        return {
            "kind": provider["kind"],
            "label": self._active_provider_option(provider["kind"])["label"],
            "provider_name": provider["provider_name"],
            "backend": provider["backend"],
            "base_url": provider["base_url"],
            "host": self._provider_host_from_base_url(provider["base_url"], ""),
            "port": self._provider_port_from_base_url(provider["base_url"], 0),
            "models": models,
            "selected_model": selected_model,
            "reachable": bool(health.get("reachable")),
            "ok": bool(health.get("ok")),
            "error": health.get("error"),
            "model_required": True,
            "auto_selected": bool(not model and selected_model),
        }

    async def update_active_provider_settings(
        self,
        payload: Mapping[str, Any],
        *,
        persist: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("active provider settings update payload must be an object")

        raw_provider = payload.get("provider", payload)
        if not isinstance(raw_provider, Mapping):
            raise ValueError("provider must be an object")
        provider = self._normalize_active_provider_payload(raw_provider)
        option = self._active_provider_option(provider["kind"])

        previous_enabled = copy.deepcopy(self.settings.plugins.enabled)
        previous_options = copy.deepcopy(self.settings.plugins.options)
        previous_default_provider = self.settings.conversation.default_provider
        previous_routes = copy.deepcopy(self.settings.conversation.routes)

        next_options = copy.deepcopy(self.settings.plugins.options)
        next_enabled = [
            str(item) for item in self.settings.plugins.enabled if str(item) != option["plugin_id"]
        ]
        next_enabled.insert(0, str(option["plugin_id"]))
        self.settings.plugins.enabled = next_enabled[:1]

        if provider["kind"] == "anthropic":
            next_options["anthropic.messages"] = {
                "providers": [
                    {
                        "provider_name": provider["provider_name"],
                        "backend": provider["backend"],
                        "base_url": provider["base_url"],
                        "model": provider["model"],
                        "api_key_env": provider["api_key_env"],
                        "timeout_seconds": provider["timeout_seconds"],
                        "health_timeout_seconds": provider["health_timeout_seconds"],
                        "temperature": provider["temperature"],
                        "max_tokens": provider["max_tokens"],
                        "headers": provider["headers"],
                        "anthropic_version": provider["anthropic_version"],
                    }
                ]
            }
        elif provider["kind"] == "llama.cpp":
            next_options["llama.cpp"] = {
                "provider_name": provider["provider_name"],
                "base_url": provider["base_url"],
                "model": provider["model"],
                "timeout_seconds": provider["timeout_seconds"],
                "health_timeout_seconds": provider["health_timeout_seconds"],
                "temperature": provider["temperature"],
                "max_tokens": provider["max_tokens"],
                "headers": provider["headers"],
            }
        else:
            next_options["openai.compat"] = {
                "providers": [
                    {
                        "provider_name": provider["provider_name"],
                        "backend": provider["backend"],
                        "base_url": provider["base_url"],
                        "model": provider["model"],
                        "api_key_env": provider["api_key_env"],
                        "timeout_seconds": provider["timeout_seconds"],
                        "health_timeout_seconds": provider["health_timeout_seconds"],
                        "temperature": provider["temperature"],
                        "max_tokens": provider["max_tokens"],
                        "headers": provider["headers"],
                    }
                ]
            }
        self.settings.plugins.options = next_options

        self.settings.conversation.default_provider = provider["provider_name"]
        for role in ("chat", "coding_agent"):
            route = self.settings.conversation.routes.setdefault(
                role,
                {"provider": provider["provider_name"], "prompt_profile": role},
            )
            route["provider"] = provider["provider_name"]
            if not str(route.get("prompt_profile", "")).strip():
                route["prompt_profile"] = "default" if role == "chat" else "coding_agent"

        self.conversations.default_provider = self.settings.conversation.default_provider
        self.conversations.routes = self._normalize_conversation_routes(self.settings)
        try:
            await self._reload_plugins()
        except Exception:
            self.settings.plugins.enabled = previous_enabled
            self.settings.plugins.options = previous_options
            self.settings.conversation.default_provider = previous_default_provider
            self.settings.conversation.routes = previous_routes
            self.conversations.default_provider = previous_default_provider
            self.conversations.routes = self._normalize_conversation_routes(self.settings)
            await self._reload_plugins()
            raise

        snapshot = self.active_provider_settings_snapshot()
        if persist:
            save_settings(self.settings)
        await self.audit.write("providers.active.updated", snapshot)
        await self.events.publish(CoreEvent("providers.active.updated", snapshot))
        return snapshot

    async def update_conversation_settings(
        self,
        payload: Mapping[str, Any],
        *,
        persist: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("conversation settings update payload must be an object")

        existing = self.conversation_settings_snapshot()
        candidate = copy.deepcopy(existing)
        for key in ("default_provider", "routes", "prompt_profiles"):
            if key in payload:
                candidate[key] = copy.deepcopy(payload[key])

        default_provider = str(candidate["default_provider"]).strip()
        if not default_provider:
            raise ValueError("default_provider must not be empty")
        if not isinstance(candidate["routes"], Mapping):
            raise ValueError("routes must be an object")
        if not isinstance(candidate["prompt_profiles"], Mapping):
            raise ValueError("prompt_profiles must be an object")

        routes: dict[str, dict[str, str]] = {}
        for role, route in candidate["routes"].items():
            if not isinstance(route, Mapping):
                raise ValueError(f"routes.{role} must be an object")
            provider = str(route.get("provider", "")).strip()
            prompt_profile = str(route.get("prompt_profile", "")).strip()
            if not provider:
                raise ValueError(f"routes.{role}.provider must not be empty")
            if not prompt_profile:
                raise ValueError(f"routes.{role}.prompt_profile must not be empty")
            self.providers.get(provider)
            routes[str(role)] = {
                "provider": provider,
                "prompt_profile": prompt_profile,
            }

        prompt_profiles: dict[str, dict[str, str]] = {}
        for name, profile in candidate["prompt_profiles"].items():
            if not isinstance(profile, Mapping):
                raise ValueError(f"prompt_profiles.{name} must be an object")
            prompt_profiles[str(name)] = {
                "personality": str(profile.get("personality", "")),
                "system_instruction": str(profile.get("system_instruction", "")),
                "tool_instruction": str(profile.get("tool_instruction", "")),
                "response_instruction": str(profile.get("response_instruction", "")),
            }

        missing_profiles = sorted(
            {
                route["prompt_profile"]
                for route in routes.values()
                if route["prompt_profile"] not in prompt_profiles
            }
        )
        if missing_profiles:
            raise ValueError(
                f"routes reference missing prompt profiles: {missing_profiles}"
            )

        self.settings.conversation.default_provider = default_provider
        self.settings.conversation.routes = routes
        self.settings.conversation.prompt_profiles = prompt_profiles
        self.conversations.default_provider = default_provider
        self.conversations.routes = self._normalize_conversation_routes(self.settings)
        self.conversations.prompt_profiles = {
            str(name): dict(profile)
            for name, profile in prompt_profiles.items()
        }
        snapshot = self.conversation_settings_snapshot()
        if persist:
            save_settings(self.settings)
        await self.audit.write("conversation.settings.updated", snapshot)
        await self.events.publish(
            CoreEvent("conversation.settings.updated", snapshot)
        )
        return snapshot

    async def update_openai_compatible_settings(
        self,
        payload: Mapping[str, Any],
        *,
        persist: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("openai.compat settings update payload must be an object")

        if "providers" not in payload:
            raise ValueError("providers is required")
        provider_items = payload["providers"]
        normalized_providers = [
            normalize_provider_config(item)
            for item in coerce_provider_configs({"providers": provider_items})
        ]
        provider_names = [item["provider_name"] for item in normalized_providers]
        duplicates = sorted(
            {
                name
                for name in provider_names
                if provider_names.count(name) > 1
            }
        )
        if duplicates:
            raise ValueError(f"duplicate provider_name values: {duplicates}")

        previous_options = copy.deepcopy(self.settings.plugins.options)
        next_options = copy.deepcopy(self.settings.plugins.options)
        next_options["openai.compat"] = {"providers": normalized_providers}
        self.settings.plugins.options = next_options
        try:
            await self._reload_plugins()
        except Exception:
            self.settings.plugins.options = previous_options
            await self._reload_plugins()
            raise

        snapshot = self.openai_compatible_settings_snapshot()
        if persist:
            save_settings(self.settings)
        await self.audit.write("providers.openai_compat.updated", snapshot)
        await self.events.publish(CoreEvent("providers.openai_compat.updated", snapshot))
        return snapshot

    async def update_anthropic_messages_settings(
        self,
        payload: Mapping[str, Any],
        *,
        persist: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("anthropic.messages settings update payload must be an object")

        if "providers" not in payload:
            raise ValueError("providers is required")
        provider_items = payload["providers"]
        normalized_providers = [
            normalize_anthropic_provider_config(item)
            for item in coerce_anthropic_provider_configs({"providers": provider_items})
        ]
        provider_names = [item["provider_name"] for item in normalized_providers]
        duplicates = sorted({name for name in provider_names if provider_names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate provider_name values: {duplicates}")

        previous_options = copy.deepcopy(self.settings.plugins.options)
        next_options = copy.deepcopy(self.settings.plugins.options)
        next_options["anthropic.messages"] = {"providers": normalized_providers}
        self.settings.plugins.options = next_options
        try:
            await self._reload_plugins()
        except Exception:
            self.settings.plugins.options = previous_options
            await self._reload_plugins()
            raise

        snapshot = self.anthropic_messages_settings_snapshot()
        if persist:
            save_settings(self.settings)
        await self.audit.write("providers.anthropic_messages.updated", snapshot)
        await self.events.publish(
            CoreEvent("providers.anthropic_messages.updated", snapshot)
        )
        return snapshot

    async def _reload_plugins(self) -> None:
        await self.plugins.stop_all()
        self.plugins = PluginManager(
            self.settings.plugins.roots,
            self.settings.plugins.enabled,
            self.registry,
            self.events,
            self.services,
            self.providers,
            self.settings.plugins.options,
        )
        await self.plugins.load_enabled()
        await self.plugins.start_all()
        configured_providers = {
            self.settings.conversation.default_provider,
            *(route["provider"] for route in self.conversations.routes.values()),
        }
        for provider_name in configured_providers:
            self.providers.get(provider_name)

    async def start(self) -> None:
        if self._started:
            return
        if "core.events" not in self.services:
            self.services.register("core.events", self.events, owner="core")
        if "core.audit" not in self.services:
            self.services.register("core.audit", self.audit, owner="core")
        if "core.settings" not in self.services:
            self.services.register("core.settings", self.settings, owner="core")
        if "core.permissions" not in self.services:
            self.services.register("core.permissions", self.permissions, owner="core")
        if "core.workspace_root" not in self.services:
            self.services.register(
                "core.workspace_root", self.workspace_root, owner="core"
            )
        if "core.todo_state" not in self.services:
            self.services.register("core.todo_state", self.todo_state, owner="core")
        if "core.shell_sessions" not in self.services:
            self.services.register("core.shell_sessions", self.shell_sessions, owner="core")
        if "core.approvals" not in self.services:
            self.services.register("core.approvals", self.approvals, owner="core")
        if "core.tool_activity" not in self.services:
            self.services.register("core.tool_activity", self.tool_activity, owner="core")
        if "desktop.session" not in self.services:
            self.services.register("desktop.session", self.desktop, owner="core")
        if "conversation.store" not in self.services:
            self.services.register(
                "conversation.store", self.conversation_store, owner="core"
            )
        if "conversation.orchestrator" not in self.services:
            self.services.register(
                "conversation.orchestrator", self.conversations, owner="core"
            )
        if not self._event_unsubscribes:
            self._event_unsubscribes = self._subscribe_tool_activity()
        self.conversations.resume()
        self.settings.core.data_dir.mkdir(parents=True, exist_ok=True)
        builtin_tools: list[Tool] = [
            ApprovalRequestTool(),
            AskUserApprovalTool(),
            EchoTool(),
            HealthTool(),
            FileReadTool(),
            FileListTool(),
            FileSearchTool(),
            FileWriteTool(),
            FileMoveTool(),
            FileDeleteTool(),
            FileEditTool(),
            ShellExecTool(),
            ShellRunTool(),
            ShellSessionTool(),
            ProcessListTool(),
            ProcessKillTool(),
            GitStatusTool(),
            GitDiffTool(),
            PackageInstallTool(),
            WorkspaceListTool(),
            WorkspaceReadTool(),
            WorkspaceSearchTool(),
            WorkspaceGrepTool(),
            WorkspaceWriteTool(),
            WorkspaceEditTool(),
            WorkspaceOpsTool(),
            TodoUpdateTool(),
        ]
        for tool in builtin_tools:
            self.registry.register(tool)
        for tool in builtin_tools:
            alias_name = CODING_AGENT_TOOL_ALIASES.get(tool.spec.name)
            if alias_name:
                self.registry.register(ToolAlias(tool, alias_name))
        self.providers.register(EchoModelProvider(), owner="core")
        try:
            await self.plugins.load_enabled()
            await self.plugins.start_all()
            configured_providers = {
                self.settings.conversation.default_provider,
                *(route["provider"] for route in self.conversations.routes.values()),
            }
            for provider_name in configured_providers:
                self.providers.get(provider_name)
        except Exception:
            await self.plugins.stop_all()
            self.registry.unregister_plugin("core")
            self.providers.unregister_owner("core")
            raise
        self._started = True
        await self.events.publish(CoreEvent("core.started", {"version": VERSION}))

    async def stop(self) -> None:
        if not self._started:
            return
        await self.events.publish(CoreEvent("core.stopping"))
        await self.conversations.shutdown()
        shutdown_approvals = getattr(self.approvals, "shutdown", None)
        if callable(shutdown_approvals):
            await shutdown_approvals()
        await self.shell_sessions.stop_all()
        await self.plugins.stop_all()
        self.registry.unregister_plugin("core")
        self.providers.unregister_owner("core")
        self.services.unregister_owner("core")
        for unsubscribe in self._event_unsubscribes:
            unsubscribe()
        self._event_unsubscribes = []
        self._started = False

    async def invoke(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        actor: str = "user",
        session_id: str | None = None,
    ) -> ToolResult:
        if not self._started:
            raise RuntimeError("YueCore must be started before invoking tools")
        return await self.executor.execute(
            ToolRequest(tool_name, arguments, actor=actor, session_id=session_id)
        )

    async def invoke_many(
        self,
        requests: list[tuple[str, dict[str, Any]]],
        *,
        actor: str = "user",
        session_id: str | None = None,
        parallel: bool = False,
    ) -> list[ToolResult]:
        if not self._started:
            raise RuntimeError("YueCore must be started before invoking tools")
        tool_requests = [
            ToolRequest(tool_name, arguments, actor=actor, session_id=session_id)
            for tool_name, arguments in requests
        ]
        return await self.executor.execute_many(tool_requests, parallel=parallel)

    async def __aenter__(self) -> "YueCore":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.stop()
