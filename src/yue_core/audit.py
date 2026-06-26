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

    def _append(self, line: str) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.write("\n")

