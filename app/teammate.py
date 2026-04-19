"""TeammateTool integration — inter-agent inbox messaging.

Uses ~/.claude/teams/*/inboxes/ for Claude Code inter-agent communication
and ~/.claude/teammate-tasks/ for shared task tracking.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

TEAMS_DIR = Path.home() / ".claude" / "teams"
TASKS_DIR = Path.home() / ".claude" / "teammate-tasks"


async def send_message(
    team: str, agent: str, message: str, sender: str = "shortcuts-agentic"
) -> dict:
    """Send a message to an agent's inbox."""
    inbox_dir = TEAMS_DIR / team / "inboxes" / agent
    inbox_dir.mkdir(parents=True, exist_ok=True)

    msg_id = uuid.uuid4().hex[:12]
    msg = {
        "id": msg_id,
        "from": sender,
        "to": agent,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    (inbox_dir / f"{msg_id}.json").write_text(json.dumps(msg, indent=2))
    logger.info("Sent message %s to %s/%s", msg_id, team, agent)
    from app.relay import broadcast_event, KIND_TEAM_MESSAGE
    asyncio.create_task(broadcast_event(KIND_TEAM_MESSAGE, message, [["team", team], ["agent", agent]]))
    return msg


async def read_inbox(team: str, agent: str) -> list[dict]:
    """Read all messages in an agent's inbox."""
    inbox_dir = TEAMS_DIR / team / "inboxes" / agent
    if not inbox_dir.exists():
        return []

    messages = []
    for f in sorted(inbox_dir.glob("*.json")):
        try:
            messages.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    return messages


async def create_task(title: str, description: str, assigned_to: str = "") -> dict:
    """Create a shared task."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    task_id = uuid.uuid4().hex[:12]
    task = {
        "id": task_id,
        "title": title,
        "description": description,
        "assigned_to": assigned_to,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    (TASKS_DIR / f"{task_id}.json").write_text(json.dumps(task, indent=2))
    from app.relay import broadcast_event, KIND_TASK_CREATED
    asyncio.create_task(broadcast_event(KIND_TASK_CREATED, title, [["task_id", task_id], ["assigned_to", assigned_to]]))
    return task


async def list_tasks() -> list[dict]:
    """List all shared tasks."""
    if not TASKS_DIR.exists():
        return []

    tasks = []
    for f in sorted(TASKS_DIR.glob("*.json")):
        try:
            tasks.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    return tasks


async def update_task_status(task_id: str, status: str) -> dict | None:
    """Update a task's status."""
    task_file = TASKS_DIR / f"{task_id}.json"
    if not task_file.exists():
        return None

    task = json.loads(task_file.read_text())
    task["status"] = status
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    task_file.write_text(json.dumps(task, indent=2))
    from app.relay import broadcast_event, KIND_TASK_UPDATED
    asyncio.create_task(broadcast_event(KIND_TASK_UPDATED, f"{task_id}: {status}", [["task_id", task_id], ["status", status]]))
    return task
