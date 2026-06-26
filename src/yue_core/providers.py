from __future__ import annotations

from collections.abc import Iterator

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

