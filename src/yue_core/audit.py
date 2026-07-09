from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from .contracts import utc_now


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    async def write(self, category: str, data: Mapping[str, Any]) -> None:
        record = {
            "timestamp": utc_now().isoformat(),
            "category": category,
            "data": dict(data),
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        async with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._append, line)

    async def recent(
        self,
        *,
        limit: int = 20,
        categories: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(int(limit), 100))
        async with self._lock:
            return await asyncio.to_thread(
                self._read_recent,
                bounded_limit,
                categories,
            )

    def _append(self, line: str) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.write("\n")

    def _read_recent(
        self,
        limit: int,
        categories: set[str] | None,
    ) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                category = str(record.get("category", ""))
                if categories is not None and category not in categories:
                    continue
                records.append(record)
        return records[-limit:][::-1]

