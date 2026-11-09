"""JSON database backups written to the configured backup directory."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.base import Base
from app.schemas.stats import BackupResult


def backup_directory() -> str:
    path = os.path.abspath(settings.backup_dir)
    os.makedirs(path, exist_ok=True)
    return path


def _as_dict(row: Any) -> Dict[str, Any]:
    data = dict(row._mapping)
    return {key: value for key, value in data.items()}


async def create_backup(session: AsyncSession) -> BackupResult:
    tables = list(Base.metadata.sorted_tables)
    payload: Dict[str, Any] = {
        "meta": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "app": settings.app_name,
            "tables": len(tables),
        },
        "tables": {},
    }
    total_rows = 0
    for table in tables:
        result = await session.execute(select(table))
        rows = [_as_dict(row) for row in result.all()]
        payload["tables"][table.name] = rows
        total_rows += len(rows)

    payload["meta"]["rows"] = total_rows
    filename = "backup-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + ".json"
    path = os.path.join(backup_directory(), filename)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, default=str)

    return BackupResult(
        filename=filename,
        path=path,
        size_bytes=os.path.getsize(path),
        created_at=payload["meta"]["created_at"],
        tables=len(tables),
        rows=total_rows,
    )


def backup_path(filename: str) -> str:
    safe = os.path.basename(filename)
    path = os.path.join(backup_directory(), safe)
    if not os.path.isfile(path):
        raise NotFoundError("Berkas backup tidak ditemukan")
    return path


def list_backups() -> List[BackupResult]:
    directory = backup_directory()
    items: List[BackupResult] = []
    for name in sorted(os.listdir(directory), reverse=True):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        tables = 0
        rows = 0
        try:
            with open(path, "r", encoding="utf-8") as handle:
                head = handle.read(4096)
            match = re.search(r'"meta"\s*:\s*(\{.*?\})', head, re.DOTALL)
            if match:
                meta = json.loads(match.group(1))
                tables = int(meta.get("tables", 0))
                rows = int(meta.get("rows", 0))
                created = meta.get("created_at", created)
        except (OSError, ValueError):
            pass
        items.append(
            BackupResult(
                filename=name,
                path=path,
                size_bytes=stat.st_size,
                created_at=created,
                tables=tables,
                rows=rows,
            )
        )
    return items
