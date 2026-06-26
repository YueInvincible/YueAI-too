from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .contracts import (
    CORE_API_VERSION,
    CoreEvent,
    EventHandler,
    ModelProvider,
    Plugin,
    Tool,
)
from .errors import PluginLoadError
from .events import EventBus
from .providers import ModelProviderRegistry
from .services import ServiceRegistry
from .tools import ToolRegistry

PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class PluginManifest:
    id: str
    version: str
    core_api: str
    entrypoint: str
    description: str = ""

    @classmethod
    def load(cls, path: Path) -> "PluginManifest":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            manifest = cls(
                id=str(raw["id"]),
                version=str(raw["version"]),
                core_api=str(raw["core_api"]),
                entrypoint=str(raw["entrypoint"]),
                description=str(raw.get("description", "")),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PluginLoadError(f"Invalid plugin manifest {path}: {exc}") from exc
        if not PLUGIN_ID_PATTERN.fullmatch(manifest.id):
            raise PluginLoadError(f"Invalid plugin id: {manifest.id}")
        if manifest.core_api.split(".", 1)[0] != CORE_API_VERSION.split(".", 1)[0]:
            raise PluginLoadError(
                f"Plugin {manifest.id} requires core API {manifest.core_api}; "
                f"running {CORE_API_VERSION}"
            )
        return manifest


class _PluginContext:
    def __init__(
        self,
        plugin_id: str,
        registry: ToolRegistry,
        events: EventBus,
        services: ServiceRegistry,
        providers: ModelProviderRegistry,
        unsubscribers: list[Callable[[], None]],
        config: dict[str, Any] | None = None,
    ) -> None:
        self.plugin_id = plugin_id
        self.config = dict(config or {})
        self._registry = registry
        self._events = events
        self._services = services
        self._providers = providers
        self._unsubscribers = unsubscribers

    def register_tool(self, tool: Tool) -> None:
        if tool.spec.plugin_id != self.plugin_id:
            raise PluginLoadError(
                f"Tool {tool.spec.name} must declare plugin_id={self.plugin_id!r}"
            )
        self._registry.register(tool)

    def register_service(self, name: str, service: Any) -> None:
        self._services.register(name, service, owner=self.plugin_id)

    def register_model_provider(self, provider: ModelProvider) -> None:
        self._providers.register(provider, owner=self.plugin_id)

    def subscribe(self, topic: str, handler: EventHandler) -> Callable[[], None]:
        unsubscribe = self._events.subscribe(topic, handler)
        self._unsubscribers.append(unsubscribe)
        return unsubscribe

    async def publish(self, event: CoreEvent) -> None:
        await self._events.publish(event)

    def get_service(self, name: str) -> Any:
        return self._services[name]


@dataclass(slots=True)
class LoadedPlugin:
    manifest: PluginManifest
    instance: Plugin
    module_name: str
    unsubscribers: list[Callable[[], None]]
    started: bool = False


class PluginManager:
    def __init__(
        self,
        roots: list[Path],
        enabled: list[str],
        registry: ToolRegistry,
        events: EventBus,
        services: ServiceRegistry,
        providers: ModelProviderRegistry,
        options: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.roots = roots
        self.enabled = set(enabled)
        self.registry = registry
        self.events = events
        self.services = services
        self.providers = providers
        self.options = options or {}
        self.loaded: dict[str, LoadedPlugin] = {}

    async def load_enabled(self) -> None:
        discovered = self.discover()
        missing = sorted(self.enabled - set(discovered))
        if missing:
            raise PluginLoadError(f"Enabled plugins not found: {missing}")
        for plugin_id in sorted(self.enabled):
            await self.load(discovered[plugin_id])

    def discover(self) -> dict[str, Path]:
        manifests: dict[str, Path] = {}
        for root in self.roots:
            if not root.exists():
                continue
            for path in root.glob("*/plugin.json"):
                manifest = PluginManifest.load(path)
                if manifest.id in manifests:
                    raise PluginLoadError(f"Duplicate plugin id: {manifest.id}")
                manifests[manifest.id] = path
        return manifests

    async def load(self, manifest_path: Path) -> None:
        manifest = PluginManifest.load(manifest_path)
        if manifest.id in self.loaded:
            raise PluginLoadError(f"Plugin already loaded: {manifest.id}")
        module_relative, separator, class_name = manifest.entrypoint.partition(":")
        if not separator or not class_name:
            raise PluginLoadError("Entrypoint must be path/to/module.py:ClassName")
        plugin_dir = manifest_path.parent.resolve()
        module_path = (plugin_dir / module_relative).resolve()
        if plugin_dir not in module_path.parents or not module_path.is_file():
            raise PluginLoadError(f"Entrypoint escapes plugin directory: {module_path}")

        module_name = f"_yue_plugin_{manifest.id.replace('.', '_')}"
        module = self._load_module(module_name, module_path)
        plugin_class = getattr(module, class_name, None)
        if plugin_class is None:
            sys.modules.pop(module_name, None)
            raise PluginLoadError(f"Plugin class not found: {class_name}")

        instance = plugin_class()
        unsubscribers: list[Callable[[], None]] = []
        context = _PluginContext(
            manifest.id,
            self.registry,
            self.events,
            self.services,
            self.providers,
            unsubscribers,
            self.options.get(manifest.id),
        )
        try:
            await instance.setup(context)
        except Exception:
            self.registry.unregister_plugin(manifest.id)
            self.services.unregister_owner(manifest.id)
            self.providers.unregister_owner(manifest.id)
            for unsubscribe in reversed(unsubscribers):
                unsubscribe()
            sys.modules.pop(module_name, None)
            raise
        self.loaded[manifest.id] = LoadedPlugin(
            manifest,
            instance,
            module_name,
            unsubscribers,
        )

    async def start_all(self) -> None:
        started: list[LoadedPlugin] = []
        try:
            for plugin in self.loaded.values():
                try:
                    await plugin.instance.start()
                except Exception:
                    try:
                        await plugin.instance.stop()
                    finally:
                        raise
                plugin.started = True
                started.append(plugin)
        except Exception:
            for plugin in reversed(started):
                await plugin.instance.stop()
                plugin.started = False
            raise

    async def stop_all(self) -> None:
        for plugin in reversed(list(self.loaded.values())):
            if plugin.started:
                await plugin.instance.stop()
            self.registry.unregister_plugin(plugin.manifest.id)
            self.services.unregister_owner(plugin.manifest.id)
            self.providers.unregister_owner(plugin.manifest.id)
            for unsubscribe in reversed(plugin.unsubscribers):
                unsubscribe()
            sys.modules.pop(plugin.module_name, None)
        self.loaded.clear()

    @staticmethod
    def _load_module(name: str, path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Unable to create module spec for {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
        return module
