"""Fire-and-forget ntfy push notifications."""

import logging
from urllib.parse import quote

import httpx

from app.config import settings

log = logging.getLogger(__name__)


async def push_result(job_id: str, result: str, conversation_id: str) -> None:
    """POST a notification to ntfy.sh. No-op if NTFY_TOPIC is unset."""
    if settings.NTFY_TOPIC is None:
        return

    click_url = (
        f"shortcuts://run-shortcut?name=AgentResult"
        f"&input=text&text={quote(job_id)}"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://ntfy.sh/{settings.NTFY_TOPIC}",
                content=result[:500],
                headers={
                    "Title": "Agent Complete",
                    "Tags": "robot",
                    "Click": click_url,
                    "Priority": "default",
                },
            )
    except Exception:
        log.exception("ntfy push failed for job %s", job_id)
