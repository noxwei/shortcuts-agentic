"""Budget tracking tests."""

from app.budget import budget_summary, check_budget, get_daily_usage, log_usage


async def test_initial_zero(db_path):
    used = await get_daily_usage()
    assert used == 0


async def test_log_increments(db_path):
    await log_usage("hello", "world response")
    used = await get_daily_usage()
    assert used == len("world response")


async def test_multiple_sums(db_path):
    await log_usage("a", "12345")
    await log_usage("b", "67890")
    used = await get_daily_usage()
    assert used == 10


async def test_check_within(db_path):
    within, remaining = await check_budget()
    assert within is True
    assert remaining > 0


async def test_check_exceeded(db_path):
    from app.config import settings
    original = settings.DAILY_CHAR_BUDGET
    settings.DAILY_CHAR_BUDGET = 5
    await log_usage("a", "123456789")  # 9 chars > budget of 5
    within, remaining = await check_budget()
    assert within is False
    assert remaining == 0
    settings.DAILY_CHAR_BUDGET = original


async def test_summary_format(db_path):
    summary = await budget_summary()
    assert "date" in summary
    assert "chars_used" in summary
    assert "chars_budget" in summary
    assert "pct" in summary
    assert isinstance(summary["pct"], float)
