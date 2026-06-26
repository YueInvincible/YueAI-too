from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any, Mapping

from .contracts import (
    AvatarExpression,
    CoreEvent,
    DesktopCommand,
    DesktopPresence,
    DesktopState,
)


class DesktopSessionManager:
    """In-process desktop state contract for the first avatar-engine slice."""

    def __init__(
        self,
        publish,
        *,
        hotkey: str = "Ctrl+Shift+Y",
        model_path: str | None = None,
        window_anchor: str = "bottom-right",
        click_opens_console: bool = True,
    ) -> None:
        self._publish = publish
        self._state = DesktopState(
            hotkey=hotkey,
            model_path=model_path,
            window_anchor=window_anchor,
            click_opens_console=click_opens_console,
        )
        self._lock = asyncio.Lock()

    def snapshot(self) -> DesktopState:
        return self._state

    async def attach(
        self,
        session_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> DesktopState:
        async with self._lock:
            sessions = list(self._state.attached_session_ids)
            if session_id not in sessions:
                sessions.append(session_id)
                self._state = replace(
                    self._state,
                    attached_session_ids=tuple(sorted(sessions)),
                )
                await self._emit(
                    "desktop.session.attached",
                    {"session_id": session_id, "metadata": dict(metadata or {})},
                )
                await self._emit_state_changed("desktop.attach")
            return self._state

    async def detach(self, session_id: str) -> DesktopState:
        async with self._lock:
            sessions = [item for item in self._state.attached_session_ids if item != session_id]
            if len(sessions) != len(self._state.attached_session_ids):
                self._state = replace(self._state, attached_session_ids=tuple(sessions))
                await self._emit("desktop.session.detached", {"session_id": session_id})
                await self._emit_state_changed("desktop.detach")
            return self._state

    async def handle_command(
        self,
        command: DesktopCommand | str,
        *,
        value: str | None = None,
        source: str = "ui",
    ) -> DesktopState:
        command = DesktopCommand(command)
        async with self._lock:
            next_state = self._reduce(command, value=value)
            if next_state != self._state:
                self._state = next_state
                await self._emit(
                    "desktop.command.handled",
                    {
                        "command": command.value,
                        "source": source,
                        "value": value,
                    },
                )
                await self._emit_state_changed(command.value)
            return self._state

    def _reduce(self, command: DesktopCommand, *, value: str | None) -> DesktopState:
        state = self._state
        if command in {
            DesktopCommand.AVATAR_CLICK,
            DesktopCommand.HOTKEY_TOGGLE_CONSOLE,
            DesktopCommand.CONSOLE_TOGGLE,
        }:
            if command is DesktopCommand.AVATAR_CLICK and not state.click_opens_console:
                return state
            return replace(state, console_open=not state.console_open)
        if command is DesktopCommand.CONSOLE_OPEN:
            return replace(state, console_open=True)
        if command is DesktopCommand.CONSOLE_CLOSE:
            return replace(state, console_open=False)
        if command is DesktopCommand.SLEEP:
            return replace(state, presence=DesktopPresence.SLEEPING)
        if command is DesktopCommand.WAKE:
            return replace(state, presence=DesktopPresence.IDLE)
        if command is DesktopCommand.SET_PRESENCE:
            if value is None:
                raise ValueError("presence.set requires a value")
            return replace(state, presence=DesktopPresence(value))
        if command is DesktopCommand.SET_EXPRESSION:
            if value is None:
                raise ValueError("expression.set requires a value")
            return replace(state, expression=AvatarExpression(value))
        raise ValueError(f"Unsupported desktop command: {command.value}")

    async def _emit_state_changed(self, reason: str) -> None:
        await self._emit(
            "desktop.state.changed",
            {
                "reason": reason,
                "state": self._state.to_dict(),
            },
        )

    async def _emit(self, topic: str, payload: Mapping[str, Any]) -> None:
        await self._publish(CoreEvent(topic, payload))
