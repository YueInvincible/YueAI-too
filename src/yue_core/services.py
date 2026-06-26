from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from .errors import YueCoreError


class ServiceRegistrationError(YueCoreError):
    pass


class ServiceRegistry(Mapping[str, Any]):
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._owners: dict[str, str] = {}

    def register(self, name: str, service: Any, *, owner: str) -> None:
        if not name or "." not in name:
            raise ServiceRegistrationError(
                "Service names must be namespaced, e.g. llm.default"
            )
        if name in self._services:
            raise ServiceRegistrationError(f"Service already registered: {name}")
        self._services[name] = service
        self._owners[name] = owner

    def unregister_owner(self, owner: str) -> None:
        names = [
            name
            for name, service_owner in self._owners.items()
            if service_owner == owner
        ]
        for name in names:
            self._services.pop(name, None)
            self._owners.pop(name, None)

    def __getitem__(self, key: str) -> Any:
        return self._services[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._services)

    def __len__(self) -> int:
        return len(self._services)

