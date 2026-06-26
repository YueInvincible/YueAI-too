from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Mapping

from .audit import AuditLog
from .builtin_tools import (
    ApprovalRequestTool,
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
from .contracts import CoreEvent, ToolRequest, ToolResult
from .desktop import DesktopSessionManager
from .events import EventBus
from .fake_provider import EchoModelProvider
from .permissions import ApprovalProvider, PermissionEngine
from .plugins import PluginManager
from .providers import ModelProviderRegistry
from .services import ServiceRegistry
from .shell_sessions import ShellSessionManager
from .tools import ToolExecutor, ToolRegistry
from .version import VERSION
from .openai_compat import coerce_provider_configs, normalize_provider_config
from .anthropic import (
    coerce_provider_configs as coerce_anthropic_provider_configs,
    normalize_provider_config as normalize_anthropic_provider_config,
)
from .approval_bridge import BridgeApprovalProvider

LOGGER = logging.getLogger(__name__)


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
        self.services.register("core.approvals", self.approvals, owner="core")
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
        self.conversations.resume()
        self.settings.core.data_dir.mkdir(parents=True, exist_ok=True)
        self.registry.register(ApprovalRequestTool())
        self.registry.register(EchoTool())
        self.registry.register(HealthTool())
        self.registry.register(FileReadTool())
        self.registry.register(FileListTool())
        self.registry.register(FileSearchTool())
        self.registry.register(FileWriteTool())
        self.registry.register(FileMoveTool())
        self.registry.register(FileDeleteTool())
        self.registry.register(FileEditTool())
        self.registry.register(ShellExecTool())
        self.registry.register(ShellRunTool())
        self.registry.register(ShellSessionTool())
        self.registry.register(ProcessListTool())
        self.registry.register(ProcessKillTool())
        self.registry.register(GitStatusTool())
        self.registry.register(GitDiffTool())
        self.registry.register(PackageInstallTool())
        self.registry.register(WorkspaceListTool())
        self.registry.register(WorkspaceReadTool())
        self.registry.register(WorkspaceSearchTool())
        self.registry.register(WorkspaceGrepTool())
        self.registry.register(WorkspaceWriteTool())
        self.registry.register(WorkspaceEditTool())
        self.registry.register(WorkspaceOpsTool())
        self.registry.register(TodoUpdateTool())
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

    async def __aenter__(self) -> "YueCore":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.stop()
