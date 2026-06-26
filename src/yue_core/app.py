from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .builtin_tools import EchoTool, HealthTool
from .config import DEFAULTS, Settings, load_settings
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
from .tools import ToolExecutor, ToolRegistry
from .version import VERSION

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
        self.services.register("core.events", self.events, owner="core")
        self.services.register("core.settings", settings, owner="core")
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
            approval_provider=approval_provider,
            interactive_approval=settings.permissions.interactive_approval,
        )
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

    async def start(self) -> None:
        if self._started:
            return
        if "core.events" not in self.services:
            self.services.register("core.events", self.events, owner="core")
        if "core.settings" not in self.services:
            self.services.register("core.settings", self.settings, owner="core")
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
        self.registry.register(EchoTool())
        self.registry.register(HealthTool())
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
