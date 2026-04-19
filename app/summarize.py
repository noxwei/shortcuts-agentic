"""Swarm result summarization -- M-6.

Collects results from multiple completed agent tasks and produces
a single summary via Gemma, then pushes it via ntfy.
"""

import logging

from app.db import get_agent_task, list_agent_tasks
from app.graph import _strip_thinking
from app.inference import chat
from app.notify import push_result

logger = logging.getLogger(__name__)


async def summarize_swarm(task_ids: list[str] | None = None) -> str:
    """Summarize results from completed agent tasks.

    If task_ids is None, summarize ALL completed tasks.
    Returns the summary text.
    """
    # Collect completed tasks
    if task_ids:
        tasks = []
        for tid in task_ids:
            t = await get_agent_task(tid)
            if t and t["status"] == "done":
                tasks.append(t)
    else:
        all_tasks = await list_agent_tasks()
        tasks = [t for t in all_tasks if t["status"] == "done"]

    if not tasks:
        return "No completed agent tasks to summarize."

    # Build context for summarization
    task_summaries = []
    for t in tasks:
        result_preview = (t["result"] or "")[:500] or "(no output)"
        task_summaries.append(
            f"Agent {t['id']} ({t['branch']}):\nPrompt: {t['prompt']}\nResult: {result_preview}"
        )

    combined = "\n\n---\n\n".join(task_summaries)

    # Ask Gemma to summarize
    summary = await chat(
        [
            {
                "role": "system",
                "content": (
                    "Summarize the following agent task results concisely. "
                    "Focus on key outcomes and any issues. Keep it under 300 words."
                ),
            },
            {"role": "user", "content": combined},
        ],
        max_tokens=400,
    )

    summary = _strip_thinking(summary)

    # Push via ntfy
    await push_result("swarm-summary", summary, "swarm")

    return summary
