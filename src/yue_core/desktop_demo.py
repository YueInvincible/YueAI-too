from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any
from uuid import uuid4

from .app import YueCore
from .config import Settings
from .contracts import (
    AvatarExpression,
    CoreEvent,
    DesktopPresence,
    DesktopState,
)


class DesktopDemoController:
    """Validated desktop-shell controller independent from any UI toolkit."""

    def __init__(self, core: YueCore, *, session_id: str = "desktop-demo") -> None:
        self.core = core
        self.session_id = session_id
        self.conversation_id: str | None = None
        self.state = core.desktop.snapshot()
        self._state_callbacks: list[Callable[[DesktopState], None]] = []
        self._message_callbacks: list[Callable[[str, str], None]] = []
        self._unsubscribe = self.core.events.subscribe("desktop.*", self._on_desktop_event)

    def on_state(self, callback: Callable[[DesktopState], None]) -> None:
        self._state_callbacks.append(callback)

    def on_message(self, callback: Callable[[str, str], None]) -> None:
        self._message_callbacks.append(callback)

    async def start(self) -> DesktopState:
        state = await self.core.desktop.attach(
            self.session_id,
            metadata={"surface": "tk-demo"},
        )
        self.state = state
        self._emit_state(state)
        return state

    async def stop(self) -> None:
        try:
            state = await self.core.desktop.detach(self.session_id)
            self.state = state
            self._emit_state(state)
        finally:
            self._unsubscribe()

    async def toggle_console(self) -> DesktopState:
        return await self._command("hotkey.toggle_console")

    async def set_presence(self, value: DesktopPresence | str) -> DesktopState:
        return await self._command(
            "presence.set",
            value=value.value if isinstance(value, DesktopPresence) else str(value),
        )

    async def set_expression(self, value: AvatarExpression | str) -> DesktopState:
        return await self._command(
            "expression.set",
            value=value.value if isinstance(value, AvatarExpression) else str(value),
        )

    async def avatar_click(self) -> DesktopState:
        return await self._command("avatar.click")

    async def sleep(self) -> DesktopState:
        return await self._command("avatar.sleep")

    async def wake(self) -> DesktopState:
        return await self._command("avatar.wake")

    async def send_chat(self, text: str, *, provider: str | None = None) -> str:
        content = text.strip()
        if not content:
            raise ValueError("Message content cannot be empty")
        if self.conversation_id is None:
            conversation = await self.core.conversations.create(title="Desktop Demo")
            self.conversation_id = conversation.id
        for callback in self._message_callbacks:
            callback("user", content)
        await self._command("presence.set", value=DesktopPresence.THINKING.value)
        assistant = await self.core.conversations.send(
            self.conversation_id,
            content,
            provider_name=provider,
            actor="desktop-demo",
            run_id=f"desktop-demo-{uuid4()}",
        )
        for callback in self._message_callbacks:
            callback("assistant", assistant.content)
        await self._command("presence.set", value=DesktopPresence.IDLE.value)
        return assistant.content

    async def _command(self, command: str, *, value: str | None = None) -> DesktopState:
        state = await self.core.desktop.handle_command(
            command,
            value=value,
            source=self.session_id,
        )
        self.state = state
        self._emit_state(state)
        return state

    async def _on_desktop_event(self, event: CoreEvent) -> None:
        if event.topic == "desktop.state.changed":
            payload = event.payload["state"]
            state = DesktopState(
                attached_session_ids=tuple(payload["attached_session_ids"]),
                console_open=bool(payload["console_open"]),
                presence=DesktopPresence(payload["presence"]),
                expression=AvatarExpression(payload["expression"]),
                hotkey=str(payload["hotkey"]),
                model_path=payload["model_path"],
                window_anchor=str(payload["window_anchor"]),
                click_opens_console=bool(payload["click_opens_console"]),
            )
            self.state = state
            self._emit_state(state)

    def _emit_state(self, state: DesktopState) -> None:
        for callback in self._state_callbacks:
            callback(state)


@dataclass(slots=True)
class DesktopRuntime:
    core: YueCore
    controller: DesktopDemoController
    loop: asyncio.AbstractEventLoop
    thread: threading.Thread

    def call(self, coroutine) -> Any:
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        return future.result()

    def shutdown(self) -> None:
        self.call(self.controller.stop())
        self.call(self.core.stop())
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)


def start_desktop_runtime(settings: Settings | None = None) -> DesktopRuntime:
    settings = settings or Settings()
    loop = asyncio.new_event_loop()
    ready: Queue[DesktopRuntime | Exception] = Queue(maxsize=1)

    def runner() -> None:
        asyncio.set_event_loop(loop)
        core = YueCore(settings)
        controller = DesktopDemoController(core)

        async def bootstrap() -> None:
            try:
                await core.start()
                await controller.start()
                ready.put(
                    DesktopRuntime(
                        core=core,
                        controller=controller,
                        loop=loop,
                        thread=thread,
                    )
                )
            except Exception as exc:
                ready.put(exc)

        loop.create_task(bootstrap())
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    thread = threading.Thread(target=runner, name="yue-desktop-demo", daemon=True)
    thread.start()
    runtime = ready.get(timeout=10)
    if isinstance(runtime, Exception):
        raise runtime
    return runtime


def run_desktop_headless_smoke_test(settings: Settings | None = None) -> dict[str, Any]:
    runtime = start_desktop_runtime(settings)
    try:
        state_before = runtime.controller.state.to_dict()
        runtime.call(runtime.controller.toggle_console())
        state_after_toggle = runtime.controller.state.to_dict()
        reply = runtime.call(runtime.controller.send_chat("hello from desktop demo"))
        return {
            "session_id": runtime.controller.session_id,
            "state_before": state_before,
            "state_after_toggle": state_after_toggle,
            "reply": reply,
            "conversation_id": runtime.controller.conversation_id,
        }
    finally:
        runtime.shutdown()


def launch_tk_desktop_demo(settings: Settings | None = None) -> None:
    import tkinter as tk
    from tkinter import ttk

    runtime = start_desktop_runtime(settings)
    updates: Queue[tuple[str, Any]] = Queue()
    runtime.controller.on_state(lambda state: updates.put(("state", state.to_dict())))
    runtime.controller.on_message(lambda role, text: updates.put(("message", (role, text))))

    root = tk.Tk()
    root.title("Yue Desktop Demo")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#101418")

    width = 220
    height = 220
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = max(0, screen_width - width - 24)
    y = max(0, screen_height - height - 72)
    root.geometry(f"{width}x{height}+{x}+{y}")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Demo.TLabel", foreground="#e7edf2", background="#101418")
    style.configure("Demo.TButton", padding=6)

    frame = tk.Frame(root, bg="#101418", highlightbackground="#2d3a45", highlightthickness=2)
    frame.pack(fill=tk.BOTH, expand=True)

    avatar = tk.Canvas(frame, width=160, height=140, bg="#101418", highlightthickness=0)
    avatar.pack(pady=(16, 4))
    avatar.create_oval(20, 10, 140, 130, fill="#2f7fda", outline="#9fd0ff", width=3, tags=("avatar",))
    avatar.create_text(80, 70, text="Yue", fill="white", font=("Segoe UI", 18, "bold"), tags=("avatar",))

    status_var = tk.StringVar(value="idle / neutral")
    console_var = tk.StringVar(value="console: closed")
    ttk.Label(frame, textvariable=status_var, style="Demo.TLabel").pack()
    ttk.Label(frame, textvariable=console_var, style="Demo.TLabel").pack(pady=(0, 12))

    console = tk.Toplevel(root)
    console.title("Yue Console")
    console.withdraw()
    console.geometry("560x360")
    console.configure(bg="#11161a")
    console.protocol("WM_DELETE_WINDOW", lambda: runtime.call(runtime.controller.toggle_console()))

    transcript = tk.Text(console, wrap="word", bg="#11161a", fg="#dce5eb", insertbackground="#dce5eb")
    transcript.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 6))

    entry_frame = tk.Frame(console, bg="#11161a")
    entry_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    entry = ttk.Entry(entry_frame)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def append_message(role: str, text: str) -> None:
        transcript.insert(tk.END, f"{role}: {text}\n\n")
        transcript.see(tk.END)

    def send_message(*_args) -> None:
        text = entry.get().strip()
        if not text:
            return
        entry.delete(0, tk.END)
        runtime.call(runtime.controller.send_chat(text))

    ttk.Button(entry_frame, text="Send", command=send_message).pack(side=tk.LEFT, padx=(8, 0))
    entry.bind("<Return>", send_message)

    def toggle_console(*_args) -> None:
        runtime.call(runtime.controller.toggle_console())

    def on_avatar_click(*_args) -> None:
        runtime.call(runtime.controller.avatar_click())

    avatar.tag_bind("avatar", "<Button-1>", on_avatar_click)
    root.bind("<Control-Shift-Y>", toggle_console)

    def process_updates() -> None:
        try:
            while True:
                kind, payload = updates.get_nowait()
                if kind == "state":
                    status_var.set(f"{payload['presence']} / {payload['expression']}")
                    console_var.set(f"console: {'open' if payload['console_open'] else 'closed'}")
                    if payload["console_open"]:
                        console.deiconify()
                        console.lift()
                    else:
                        console.withdraw()
                elif kind == "message":
                    role, text = payload
                    append_message(role, text)
        except Empty:
            pass
        root.after(50, process_updates)

    def shutdown() -> None:
        runtime.shutdown()
        try:
            console.destroy()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", shutdown)
    process_updates()
    root.mainloop()
