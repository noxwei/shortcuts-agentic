"""Audit logging — log all API calls to SQLite."""

from datetime import datetime, timezone

import aiosqlite

from app.db import _resolve_db_path


async def init_audit_table() -> None:
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user TEXT,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER,
                body_preview TEXT
            )
        """)
        await db.commit()


async def log_request(user: str | None, method: str, path: str, status_code: int, body_preview: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute(
            "INSERT INTO audit_log (timestamp, user, method, path, status_code, body_preview) VALUES (?, ?, ?, ?, ?, ?)",
            (now, user, method, path, status_code, body_preview[:200] if body_preview else ""),
        )
        await db.commit()


async def get_recent_logs(limit: int = 100) -> list[dict]:
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
