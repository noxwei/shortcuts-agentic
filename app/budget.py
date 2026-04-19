"""Daily token budget tracking via character-count approximation.

Gemma MLX doesn't return token counts, so we approximate:
1 token ~= 4 characters.
"""

from datetime import date, datetime, timezone

import aiosqlite

from app.config import settings
from app.db import _resolve_db_path


async def init_usage_table() -> None:
    """Create the usage table if it doesn't exist."""
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                chars_in INTEGER NOT NULL,
                chars_out INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def log_usage(input_text: str, output_text: str) -> None:
    """Record a usage row for today."""
    now = datetime.now(timezone.utc).isoformat()
    today = date.today().isoformat()
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        await db.execute(
            "INSERT INTO usage (date, chars_in, chars_out, created_at) VALUES (?, ?, ?, ?)",
            (today, len(input_text), len(output_text), now),
        )
        await db.commit()


async def get_daily_usage() -> int:
    """Sum chars_out for today's date."""
    today = date.today().isoformat()
    async with aiosqlite.connect(str(_resolve_db_path())) as db:
        async with db.execute(
            "SELECT COALESCE(SUM(chars_out), 0) FROM usage WHERE date = ?",
            (today,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


async def check_budget() -> tuple[bool, int]:
    """Check if within daily budget. Returns (within_budget, chars_remaining)."""
    used = await get_daily_usage()
    remaining = settings.DAILY_CHAR_BUDGET - used
    return remaining > 0, max(remaining, 0)


async def budget_summary() -> dict:
    """Return a summary dict of today's budget status."""
    used = await get_daily_usage()
    budget = settings.DAILY_CHAR_BUDGET
    return {
        "date": date.today().isoformat(),
        "chars_used": used,
        "chars_budget": budget,
        "pct": round(used / budget * 100, 1) if budget > 0 else 0,
    }
