"""Async SQLite helpers for job and conversation persistence."""

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.config import settings

_db_path: Path | None = None


def _resolve_db_path() -> Path:
    global _db_path
    if _db_path is None:
        _db_path = Path(settings.DB_PATH).expanduser()
    return _db_path


async def init_db() -> None:
    path = _resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(path)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                source TEXT,
                input_text TEXT,
                result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                messages TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id TEXT PRIMARY KEY,
                prompt TEXT,
                repo TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                worktree_path TEXT,
                branch TEXT,
                result TEXT,
                diff_summary TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                pid INTEGER
            )
        """)
        await db.commit()
    # Usage table lives in the same DB — initialized separately to keep budget.py self-contained.
    from app.budget import init_usage_table
    await init_usage_table()


async def load_conversation(conversation_id: str) -> list[dict]:
    """Load message history for a conversation. Returns [] if not found."""
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        async with db.execute(
            "SELECT messages FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return []
            return json.loads(row[0])


async def save_conversation(conversation_id: str, messages: list[dict]) -> None:
    """Upsert conversation message history."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute(
            "INSERT INTO conversations (conversation_id, messages, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(conversation_id) DO UPDATE SET messages = ?, updated_at = ?",
            (conversation_id, json.dumps(messages), now, json.dumps(messages), now),
        )
        await db.commit()


async def create_job(job_id: str, conversation_id: str, source: str, text: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute(
            "INSERT INTO jobs (id, conversation_id, status, source, input_text, created_at, updated_at) "
            "VALUES (?, ?, 'queued', ?, ?, ?, ?)",
            (job_id, conversation_id, source, text, now, now),
        )
        await db.commit()


async def get_job(job_id: str) -> dict | None:
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)


async def update_job(job_id: str, status: str, result: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        if result is not None:
            await db.execute(
                "UPDATE jobs SET status = ?, result = ?, updated_at = ? WHERE id = ?",
                (status, result, now, job_id),
            )
        else:
            await db.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, job_id),
            )
        await db.commit()


async def create_agent_task(task_id: str, prompt: str, repo: str, branch: str, worktree_path: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute(
            "INSERT INTO agent_tasks (id, prompt, repo, status, branch, worktree_path, created_at, updated_at) "
            "VALUES (?, ?, ?, 'queued', ?, ?, ?, ?)",
            (task_id, prompt, repo, branch, worktree_path, now, now),
        )
        await db.commit()


async def get_agent_task(task_id: str) -> dict | None:
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_agent_task(task_id: str, **kwargs) -> None:
    now = datetime.now(timezone.utc).isoformat()
    kwargs["updated_at"] = now
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [task_id]
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute(f"UPDATE agent_tasks SET {sets} WHERE id = ?", vals)
        await db.commit()


async def list_agent_tasks() -> list[dict]:
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM agent_tasks ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


def get_agent_task_sync(task_id: str) -> dict | None:
    import sqlite3
    path = str(_resolve_db_path())
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_agent_tasks_sync() -> list[dict]:
    import sqlite3
    path = str(_resolve_db_path())
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT id, prompt, status, branch, created_at, updated_at FROM agent_tasks ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
