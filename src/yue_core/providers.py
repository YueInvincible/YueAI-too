from __future__ import annotations

from collections.abc import Iterator
import asyncio
from typing import Any

from .contracts import ModelProvider
from .errors import YueCoreError


class ProviderRegistrationError(YueCoreError):
    pass


class ModelProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}
        self._owners: dict[str, str] = {}

    def register(self, provider: ModelProvider, *, owner: str) -> None:
        name = provider.name
        if not name or "." not in name:
            raise ProviderRegistrationError(
                "Provider names must be namespaced, e.g. llama.local"
            )
        if name in self._providers:
            raise ProviderRegistrationError(f"Provider already registered: {name}")
        self._providers[name] = provider
        self._owners[name] = owner

    def get(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise KeyError(f"Unknown model provider: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._providers)

    def unregister_owner(self, owner: str) -> None:
        names = [name for name, provider_owner in self._owners.items() if provider_owner == owner]
        for name in names:
            self._providers.pop(name, None)
            self._owners.pop(name, None)

    def __iter__(self) -> Iterator[str]:
        return iter(self._providers)

    async def health(self) -> list[dict[str, Any]]:
        results = await asyncio.gather(
            *(self._provider_health(name, provider) for name, provider in self._providers.items())
        )
        return sorted(results, key=lambda item: item["provider"])

    async def _provider_health(
        self,
        name: str,
        provider: ModelProvider,
    ) -> dict[str, Any]:
        health_fn = getattr(provider, "health", None)
        if health_fn is None:
            return {
                "provider": name,
                "ok": True,
                "reachable": None,
                "details": "health() not implemented",
            }
        try:
            payload = await health_fn()
        except Exception as exc:
            return {
                "provider": name,
                "ok": False,
                "reachable": False,
                "error": str(exc),
            }
        if not isinstance(payload, dict):
            raise ProviderRegistrationError(
                f"Provider health() must return a dict for {name}"
            )
        normalized = {"provider": name, **payload}
        normalized["provider"] = name
        normalized.setdefault("ok", True)
        return normalized

