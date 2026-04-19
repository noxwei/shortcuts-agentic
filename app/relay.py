"""Nostr relay integration — broadcast agent lifecycle events."""

import time
import uuid

import httpx
import structlog

logger = structlog.get_logger()

RELAY_URL = "http://127.0.0.1:8201/relay/broadcast"
RELAY_EVENTS_URL = "http://127.0.0.1:8201/relay/events"

KIND_AGENT_SPAWN = 1000
KIND_AGENT_DONE = 1001
KIND_AGENT_FAILED = 1002
KIND_TEAM_MESSAGE = 1003
KIND_TASK_CREATED = 1004
KIND_TASK_UPDATED = 1005


async def broadcast_event(kind: int, content: str, tags: list | None = None) -> None:
    event = {
        "id": uuid.uuid4().hex,
        "kind": kind,
        "content": content,
        "tags": tags or [],
        "pubkey": "shortcuts-agentic",
        "created_at": int(time.time()),
        "sig": "",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(RELAY_URL, json=event)
            resp.raise_for_status()
            logger.info("relay_broadcast", kind=kind, content=content[:50])
    except httpx.ConnectError:
        logger.warning("relay_unavailable", kind=kind)
    except httpx.HTTPStatusError as e:
        logger.warning("relay_error", kind=kind, status=e.response.status_code)
    except Exception as e:
        logger.warning("relay_broadcast_failed", kind=kind, error=str(e))


async def subscribe_events(kinds: list[int] | None = None, since: int = 0) -> list[dict]:
    params: dict = {}
    if kinds:
        params["kind"] = ",".join(str(k) for k in kinds)
    if since:
        params["since"] = str(since)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(RELAY_EVENTS_URL, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        logger.warning("relay_subscribe_failed")
        return []
