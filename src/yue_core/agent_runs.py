from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import utc_now
from .errors import YueCoreError


class AgentRunError(YueCoreError):
    pass


class AgentRunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    VERIFYING = "verifying"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_AGENT_RUN_STATUSES = frozenset(
    {
        AgentRunStatus.CREATED,
        AgentRunStatus.RUNNING,
        AgentRunStatus.WAITING_APPROVAL,
        AgentRunStatus.VERIFYING,
    }
)


class AgentRunStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class AgentRunVerificationStatus(str, Enum):
    NOT_RUN = "not_run"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class AgentRunChecklistItem:
    id: str
    text: str
    status: AgentRunStepStatus = AgentRunStepStatus.PENDING
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "text": self.text,
            "status": self.status.value,
            "note": self.note,
        }


def _checklist_from_plan(plan: Sequence[str]) -> tuple[AgentRunChecklistItem, ...]:
    return tuple(
        AgentRunChecklistItem(id=f"step-{index + 1}", text=str(item))
        for index, item in enumerate(plan)
        if str(item).strip()
    )


def _coerce_checklist(
    items: Sequence[Mapping[str, Any]] | Sequence[AgentRunChecklistItem] | None,
    *,
    fallback_plan: Sequence[str] = (),
) -> tuple[AgentRunChecklistItem, ...]:
    if items is None:
        return _checklist_from_plan(fallback_plan)
    result: list[AgentRunChecklistItem] = []
    for index, item in enumerate(items):
        if isinstance(item, AgentRunChecklistItem):
            result.append(item)
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            raise AgentRunError(f"checklist[{index}].text must not be empty")
        raw_status = str(item.get("status", AgentRunStepStatus.PENDING.value))
        result.append(
            AgentRunChecklistItem(
                id=str(item.get("id") or f"step-{index + 1}"),
                text=text,
                status=AgentRunStepStatus(raw_status),
                note=str(item.get("note", "")),
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class AgentRun:
    id: str
    conversation_id: str
    user_request: str
    provider_role: str = "coding_agent"
    status: AgentRunStatus = AgentRunStatus.CREATED
    plan: tuple[str, ...] = ()
    checklist: tuple[AgentRunChecklistItem, ...] = ()
    verification_status: AgentRunVerificationStatus = AgentRunVerificationStatus.NOT_RUN
    verification_summary: str = ""
    persona_snapshot: Mapping[str, Any] = field(default_factory=dict)
    provider_snapshot: Mapping[str, Any] = field(default_factory=dict)
    tool_references: tuple[Mapping[str, Any], ...] = ()
    approval_references: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    response_message_id: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_request": self.user_request,
            "provider_role": self.provider_role,
            "status": self.status.value,
            "plan": list(self.plan),
            "checklist": [item.to_dict() for item in self.checklist],
            "verification": {
                "status": self.verification_status.value,
                "summary": self.verification_summary,
            },
            "persona_snapshot": dict(self.persona_snapshot or {}),
            "provider_snapshot": dict(self.provider_snapshot or {}),
            "tool_references": [dict(item) for item in self.tool_references],
            "approval_references": [dict(item) for item in self.approval_references],
            "metadata": dict(self.metadata or {}),
            "response_message_id": self.response_message_id,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AgentRunStore:
    async def create(
        self,
        *,
        conversation_id: str,
        user_request: str,
        provider_role: str = "coding_agent",
        run_id: str | None = None,
        plan: Sequence[str] = (),
        checklist: Sequence[Mapping[str, Any]] | None = None,
        persona_snapshot: Mapping[str, Any] | None = None,
        provider_snapshot: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentRun:
        raise NotImplementedError

    async def get(self, run_id: str) -> AgentRun | None:
        raise NotImplementedError

    async def list(self, *, limit: int = 100) -> Sequence[AgentRun]:
        raise NotImplementedError

    async def list_active(self) -> Sequence[AgentRun]:
        raise NotImplementedError

    async def update(
        self,
        run_id: str,
        *,
        status: AgentRunStatus | None = None,
        plan: Sequence[str] | None = None,
        checklist: Sequence[Mapping[str, Any]] | None = None,
        verification_status: AgentRunVerificationStatus | None = None,
        verification_summary: str | None = None,
        persona_snapshot: Mapping[str, Any] | None = None,
        provider_snapshot: Mapping[str, Any] | None = None,
        tool_references: Sequence[Mapping[str, Any]] | None = None,
        approval_references: Sequence[Mapping[str, Any]] | None = None,
        metadata: Mapping[str, Any] | None = None,
        response_message_id: str | None = None,
        error: str | None = None,
        completed: bool = False,
    ) -> AgentRun:
        raise NotImplementedError


class InMemoryAgentRunStore(AgentRunStore):
    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        conversation_id: str,
        user_request: str,
        provider_role: str = "coding_agent",
        run_id: str | None = None,
        plan: Sequence[str] = (),
        checklist: Sequence[Mapping[str, Any]] | None = None,
        persona_snapshot: Mapping[str, Any] | None = None,
        provider_snapshot: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentRun:
        run = AgentRun(
            id=run_id or str(uuid4()),
            conversation_id=conversation_id,
            user_request=user_request,
            provider_role=provider_role,
            plan=tuple(str(item) for item in plan),
            checklist=_coerce_checklist(checklist, fallback_plan=plan),
            persona_snapshot=dict(persona_snapshot or {}),
            provider_snapshot=dict(provider_snapshot or {}),
            metadata=dict(metadata or {}),
        )
        async with self._lock:
            if run.id in self._runs:
                raise AgentRunError(f"Agent run already exists: {run.id}")
            self._runs[run.id] = run
        return run

    async def get(self, run_id: str) -> AgentRun | None:
        async with self._lock:
            return self._runs.get(run_id)

    async def list(self, *, limit: int = 100) -> Sequence[AgentRun]:
        async with self._lock:
            runs = sorted(
                self._runs.values(),
                key=lambda item: item.updated_at,
                reverse=True,
            )
            return tuple(runs[: max(0, limit)])

    async def list_active(self) -> Sequence[AgentRun]:
        async with self._lock:
            return tuple(
                run
                for run in self._runs.values()
                if run.status in ACTIVE_AGENT_RUN_STATUSES
            )

    async def update(
        self,
        run_id: str,
        *,
        status: AgentRunStatus | None = None,
        plan: Sequence[str] | None = None,
        checklist: Sequence[Mapping[str, Any]] | None = None,
        verification_status: AgentRunVerificationStatus | None = None,
        verification_summary: str | None = None,
        persona_snapshot: Mapping[str, Any] | None = None,
        provider_snapshot: Mapping[str, Any] | None = None,
        tool_references: Sequence[Mapping[str, Any]] | None = None,
        approval_references: Sequence[Mapping[str, Any]] | None = None,
        metadata: Mapping[str, Any] | None = None,
        response_message_id: str | None = None,
        error: str | None = None,
        completed: bool = False,
    ) -> AgentRun:
        async with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise AgentRunError(f"Agent run does not exist: {run_id}")
            updated = replace(
                current,
                status=status or current.status,
                plan=tuple(str(item) for item in plan) if plan is not None else current.plan,
                checklist=(
                    _coerce_checklist(checklist)
                    if checklist is not None
                    else current.checklist
                ),
                verification_status=verification_status or current.verification_status,
                verification_summary=(
                    verification_summary
                    if verification_summary is not None
                    else current.verification_summary
                ),
                persona_snapshot=(
                    dict(persona_snapshot)
                    if persona_snapshot is not None
                    else current.persona_snapshot
                ),
                provider_snapshot=(
                    dict(provider_snapshot)
                    if provider_snapshot is not None
                    else current.provider_snapshot
                ),
                tool_references=(
                    tuple(dict(item) for item in tool_references)
                    if tool_references is not None
                    else current.tool_references
                ),
                approval_references=(
                    tuple(dict(item) for item in approval_references)
                    if approval_references is not None
                    else current.approval_references
                ),
                metadata=dict(metadata) if metadata is not None else current.metadata,
                response_message_id=(
                    response_message_id
                    if response_message_id is not None
                    else current.response_message_id
                ),
                error=error,
                updated_at=utc_now(),
                completed_at=utc_now() if completed else current.completed_at,
            )
            self._runs[run_id] = updated
            return updated


class SQLiteAgentRunStore(AgentRunStore):
    SCHEMA_VERSION = 3

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._initialize_sync)
            self._initialized = True

    async def create(
        self,
        *,
        conversation_id: str,
        user_request: str,
        provider_role: str = "coding_agent",
        run_id: str | None = None,
        plan: Sequence[str] = (),
        checklist: Sequence[Mapping[str, Any]] | None = None,
        persona_snapshot: Mapping[str, Any] | None = None,
        provider_snapshot: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentRun:
        await self.initialize()
        run = AgentRun(
            id=run_id or str(uuid4()),
            conversation_id=conversation_id,
            user_request=user_request,
            provider_role=provider_role,
            plan=tuple(str(item) for item in plan),
            checklist=_coerce_checklist(checklist, fallback_plan=plan),
            persona_snapshot=dict(persona_snapshot or {}),
            provider_snapshot=dict(provider_snapshot or {}),
            metadata=dict(metadata or {}),
        )
        async with self._lock:
            await asyncio.to_thread(self._insert_sync, run)
        return run

    async def get(self, run_id: str) -> AgentRun | None:
        await self.initialize()
        async with self._lock:
            row = await asyncio.to_thread(self._get_sync, run_id)
        return self._from_row(row) if row else None

    async def list(self, *, limit: int = 100) -> Sequence[AgentRun]:
        await self.initialize()
        async with self._lock:
            rows = await asyncio.to_thread(self._list_sync, max(0, limit))
        return tuple(self._from_row(row) for row in rows)

    async def list_active(self) -> Sequence[AgentRun]:
        await self.initialize()
        async with self._lock:
            rows = await asyncio.to_thread(self._list_active_sync)
        return tuple(self._from_row(row) for row in rows)

    async def update(
        self,
        run_id: str,
        *,
        status: AgentRunStatus | None = None,
        plan: Sequence[str] | None = None,
        checklist: Sequence[Mapping[str, Any]] | None = None,
        verification_status: AgentRunVerificationStatus | None = None,
        verification_summary: str | None = None,
        persona_snapshot: Mapping[str, Any] | None = None,
        provider_snapshot: Mapping[str, Any] | None = None,
        tool_references: Sequence[Mapping[str, Any]] | None = None,
        approval_references: Sequence[Mapping[str, Any]] | None = None,
        metadata: Mapping[str, Any] | None = None,
        response_message_id: str | None = None,
        error: str | None = None,
        completed: bool = False,
    ) -> AgentRun:
        await self.initialize()
        async with self._lock:
            current_row = await asyncio.to_thread(self._get_sync, run_id)
            if current_row is None:
                raise AgentRunError(f"Agent run does not exist: {run_id}")
            current = self._from_row(current_row)
            updated = replace(
                current,
                status=status or current.status,
                plan=tuple(str(item) for item in plan) if plan is not None else current.plan,
                checklist=(
                    _coerce_checklist(checklist)
                    if checklist is not None
                    else current.checklist
                ),
                verification_status=verification_status or current.verification_status,
                verification_summary=(
                    verification_summary
                    if verification_summary is not None
                    else current.verification_summary
                ),
                persona_snapshot=(
                    dict(persona_snapshot)
                    if persona_snapshot is not None
                    else current.persona_snapshot
                ),
                provider_snapshot=(
                    dict(provider_snapshot)
                    if provider_snapshot is not None
                    else current.provider_snapshot
                ),
                tool_references=(
                    tuple(dict(item) for item in tool_references)
                    if tool_references is not None
                    else current.tool_references
                ),
                approval_references=(
                    tuple(dict(item) for item in approval_references)
                    if approval_references is not None
                    else current.approval_references
                ),
                metadata=dict(metadata) if metadata is not None else current.metadata,
                response_message_id=(
                    response_message_id
                    if response_message_id is not None
                    else current.response_message_id
                ),
                error=error,
                updated_at=utc_now(),
                completed_at=utc_now() if completed else current.completed_at,
            )
            await asyncio.to_thread(self._update_sync, updated)
        return updated

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize_sync(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_run_schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_request TEXT NOT NULL,
                    provider_role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    checklist_json TEXT NOT NULL DEFAULT '[]',
                    verification_status TEXT NOT NULL DEFAULT 'not_run',
                    verification_summary TEXT NOT NULL DEFAULT '',
                    persona_snapshot_json TEXT NOT NULL DEFAULT '{}',
                    provider_snapshot_json TEXT NOT NULL DEFAULT '{}',
                    tool_references_json TEXT NOT NULL DEFAULT '[]',
                    approval_references_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL,
                    response_message_id TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_agent_runs_updated_at
                    ON agent_runs(updated_at);
                CREATE INDEX IF NOT EXISTS idx_agent_runs_conversation
                    ON agent_runs(conversation_id);
                """
            )
            current = connection.execute(
                "SELECT value FROM agent_run_schema_info WHERE key = 'version'"
            ).fetchone()
            if current is None:
                connection.execute(
                    "INSERT INTO agent_run_schema_info(key, value) VALUES('version', ?)",
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(current["value"]) < self.SCHEMA_VERSION:
                self._migrate_sync(connection, int(current["value"]))
                connection.execute(
                    "UPDATE agent_run_schema_info SET value = ? WHERE key = 'version'",
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(current["value"]) != self.SCHEMA_VERSION:
                raise AgentRunError(
                    f"Unsupported agent run schema version: {current['value']}"
                )

    def _migrate_sync(self, connection: sqlite3.Connection, version: int) -> None:
        if version < 2:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(agent_runs)").fetchall()
            }
            if "checklist_json" not in columns:
                connection.execute(
                    "ALTER TABLE agent_runs ADD COLUMN checklist_json TEXT NOT NULL DEFAULT '[]'"
                )
            if "verification_status" not in columns:
                connection.execute(
                    "ALTER TABLE agent_runs ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'not_run'"
                )
            if "verification_summary" not in columns:
                connection.execute(
                    "ALTER TABLE agent_runs ADD COLUMN verification_summary TEXT NOT NULL DEFAULT ''"
                )
        if version < 3:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(agent_runs)").fetchall()
            }
            if "persona_snapshot_json" not in columns:
                connection.execute(
                    "ALTER TABLE agent_runs ADD COLUMN persona_snapshot_json TEXT NOT NULL DEFAULT '{}'"
                )
            if "provider_snapshot_json" not in columns:
                connection.execute(
                    "ALTER TABLE agent_runs ADD COLUMN provider_snapshot_json TEXT NOT NULL DEFAULT '{}'"
                )
            if "tool_references_json" not in columns:
                connection.execute(
                    "ALTER TABLE agent_runs ADD COLUMN tool_references_json TEXT NOT NULL DEFAULT '[]'"
                )
            if "approval_references_json" not in columns:
                connection.execute(
                    "ALTER TABLE agent_runs ADD COLUMN approval_references_json TEXT NOT NULL DEFAULT '[]'"
                )

    def _insert_sync(self, run: AgentRun) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs(
                    id, conversation_id, user_request, provider_role, status,
                    plan_json, checklist_json, verification_status,
                    verification_summary, persona_snapshot_json,
                    provider_snapshot_json, tool_references_json,
                    approval_references_json, metadata_json, response_message_id, error,
                    created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._row_values(run),
            )

    def _update_sync(self, run: AgentRun) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE agent_runs
                SET conversation_id = ?,
                    user_request = ?,
                    provider_role = ?,
                    status = ?,
                    plan_json = ?,
                    checklist_json = ?,
                    verification_status = ?,
                    verification_summary = ?,
                    persona_snapshot_json = ?,
                    provider_snapshot_json = ?,
                    tool_references_json = ?,
                    approval_references_json = ?,
                    metadata_json = ?,
                    response_message_id = ?,
                    error = ?,
                    created_at = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    run.conversation_id,
                    run.user_request,
                    run.provider_role,
                    run.status.value,
                    self._json(run.plan),
                    self._json([item.to_dict() for item in run.checklist]),
                    run.verification_status.value,
                    run.verification_summary,
                    self._json(run.persona_snapshot or {}),
                    self._json(run.provider_snapshot or {}),
                    self._json(run.tool_references),
                    self._json(run.approval_references),
                    self._json(run.metadata or {}),
                    run.response_message_id,
                    run.error,
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.id,
                ),
            )

    def _get_sync(self, run_id: str):
        with self._connection() as connection:
            return connection.execute(
                "SELECT * FROM agent_runs WHERE id = ?",
                (run_id,),
            ).fetchone()

    def _list_sync(self, limit: int):
        with self._connection() as connection:
            return connection.execute(
                """
                SELECT * FROM agent_runs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def _list_active_sync(self):
        statuses = tuple(status.value for status in ACTIVE_AGENT_RUN_STATUSES)
        placeholders = ", ".join("?" for _ in statuses)
        with self._connection() as connection:
            return connection.execute(
                f"""
                SELECT * FROM agent_runs
                WHERE status IN ({placeholders})
                ORDER BY updated_at ASC
                """,
                statuses,
            ).fetchall()

    @classmethod
    def _row_values(cls, run: AgentRun) -> tuple[Any, ...]:
        return (
            run.id,
            run.conversation_id,
            run.user_request,
            run.provider_role,
            run.status.value,
            cls._json(run.plan),
            cls._json([item.to_dict() for item in run.checklist]),
            run.verification_status.value,
            run.verification_summary,
            cls._json(run.persona_snapshot or {}),
            cls._json(run.provider_snapshot or {}),
            cls._json(run.tool_references),
            cls._json(run.approval_references),
            cls._json(run.metadata or {}),
            run.response_message_id,
            run.error,
            run.created_at.isoformat(),
            run.updated_at.isoformat(),
            run.completed_at.isoformat() if run.completed_at else None,
        )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))

    @staticmethod
    def _from_row(row: sqlite3.Row) -> AgentRun:
        return AgentRun(
            id=row["id"],
            conversation_id=row["conversation_id"],
            user_request=row["user_request"],
            provider_role=row["provider_role"],
            status=AgentRunStatus(row["status"]),
            plan=tuple(str(item) for item in json.loads(row["plan_json"])),
            checklist=_coerce_checklist(json.loads(row["checklist_json"])),
            verification_status=AgentRunVerificationStatus(row["verification_status"]),
            verification_summary=row["verification_summary"],
            persona_snapshot=json.loads(row["persona_snapshot_json"]),
            provider_snapshot=json.loads(row["provider_snapshot_json"]),
            tool_references=tuple(json.loads(row["tool_references_json"])),
            approval_references=tuple(json.loads(row["approval_references_json"])),
            metadata=json.loads(row["metadata_json"]),
            response_message_id=row["response_message_id"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
        )
