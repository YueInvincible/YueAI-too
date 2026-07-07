from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .builtin_tools import _sanitize_command_output
from .shell_utils import build_shell_argv


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _shell_argv(command: str) -> list[str]:
    return build_shell_argv(command)


@dataclass(slots=True)
class ShellSession:
    session_id: str
    command: str
    cwd: str
    argv: list[str]
    process: asyncio.subprocess.Process
    started_at: datetime = field(default_factory=_utc_now)
    stdout_chunks: list[str] = field(default_factory=list)
    stderr_chunks: list[str] = field(default_factory=list)
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    reader_tasks: list[asyncio.Task[None]] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        stdout_text, stdout_truncated = _sanitize_command_output("".join(self.stdout_chunks))
        stderr_text, stderr_truncated = _sanitize_command_output("".join(self.stderr_chunks))
        return {
            "session_id": self.session_id,
            "command": self.command,
            "cwd": self.cwd,
            "argv": self.argv,
            "pid": self.process.pid,
            "running": self.process.returncode is None,
            "exit_code": self.process.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "stdout_truncated": self.stdout_truncated or stdout_truncated,
            "stderr_truncated": self.stderr_truncated or stderr_truncated,
            "started_at": self.started_at.isoformat(),
        }


class ShellSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ShellSession] = {}
        self._lock = asyncio.Lock()

    async def start(self, session_id: str, command: str, cwd: Path) -> dict[str, Any]:
        async with self._lock:
            existing = self._sessions.get(session_id)
            if existing and existing.process.returncode is None:
                raise ValueError(f"Shell session already running: {session_id}")
            process = await asyncio.create_subprocess_exec(
                *_shell_argv(command),
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            session = ShellSession(
                session_id=session_id,
                command=command,
                cwd=str(cwd),
                argv=_shell_argv(command),
                process=process,
            )
            session.reader_tasks = [
                asyncio.create_task(
                    self._drain_stream(
                        session,
                        process.stdout,
                        session.stdout_chunks,
                        truncate_flag="stdout_truncated",
                    )
                ),
                asyncio.create_task(
                    self._drain_stream(
                        session,
                        process.stderr,
                        session.stderr_chunks,
                        truncate_flag="stderr_truncated",
                    )
                ),
            ]
            self._sessions[session_id] = session
            return session.snapshot()

    async def read(self, session_id: str) -> dict[str, Any]:
        session = await self._require_session(session_id)
        return session.snapshot()

    async def stop(self, session_id: str) -> dict[str, Any]:
        session = await self._require_session(session_id)
        if session.process.returncode is None:
            session.process.kill()
            await session.process.wait()
        await self._finalize_readers(session)
        return session.snapshot()

    async def list(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [self._sessions[key].snapshot() for key in sorted(self._sessions)]

    async def stop_all(self) -> None:
        async with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            if session.process.returncode is None:
                session.process.kill()
                with contextlib.suppress(Exception):
                    await session.process.wait()
            await self._finalize_readers(session)

    async def _require_session(self, session_id: str) -> ShellSession:
        async with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown shell session: {session_id}")
        return session

    async def _finalize_readers(self, session: ShellSession) -> None:
        for task in session.reader_tasks:
            with contextlib.suppress(Exception):
                await task

    async def _drain_stream(
        self,
        session: ShellSession,
        stream: asyncio.StreamReader | None,
        chunks: list[str],
        *,
        truncate_flag: str,
    ) -> None:
        if stream is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                break
            chunks.append(line.decode("utf-8", errors="replace"))
            if sum(len(item) for item in chunks) > 200000:
                setattr(session, truncate_flag, True)
                del chunks[:-200]
