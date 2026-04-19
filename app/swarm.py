"""Swarm manager — spawn and track claude CLI instances in git worktrees."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class AgentTask:
    id: str
    prompt: str
    repo: str  # path to the git repo to work in
    status: str = "queued"  # queued, running, done, failed
    worktree_path: str = ""
    branch: str = ""
    result: str = ""
    diff_summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pid: int | None = None


# In-memory registry of active agent tasks
_tasks: dict[str, AgentTask] = {}


def _task_from_row(row: dict) -> AgentTask:
    return AgentTask(
        id=row["id"], prompt=row["prompt"] or "", repo=row["repo"] or "",
        status=row["status"], worktree_path=row["worktree_path"] or "",
        branch=row["branch"] or "", result=row["result"] or "",
        diff_summary=row.get("diff_summary") or "",
        created_at=row["created_at"], updated_at=row["updated_at"],
        pid=row.get("pid"),
    )


async def _persist_task(task: AgentTask) -> None:
    from app.db import create_agent_task
    await create_agent_task(task.id, task.prompt, task.repo, task.branch, task.worktree_path)


async def _update_task_db(task: AgentTask, **kwargs) -> None:
    from app.db import update_agent_task
    await update_agent_task(task.id, **kwargs)


async def _capture_diff_summary(task: AgentTask) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "diff", "--stat",
            cwd=task.worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        return stdout.decode(errors="replace")[:1000]
    except Exception:
        return ""


async def spawn_agent(prompt: str, repo: str = "~/Local_Dev") -> AgentTask:
    """Spawn a claude CLI instance in an isolated git worktree."""
    task_id = uuid.uuid4().hex[:12]
    repo_path = Path(repo).expanduser()
    branch = f"agent-{task_id}"
    worktree_path = repo_path / ".worktrees" / branch

    task = AgentTask(
        id=task_id,
        prompt=prompt,
        repo=str(repo_path),
        branch=branch,
        worktree_path=str(worktree_path),
    )
    _tasks[task_id] = task
    await _persist_task(task)

    # Create worktree
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "worktree", "add", str(worktree_path), "-b", branch,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            task.status = "failed"
            task.result = f"Failed to create worktree: {stderr.decode()}"
            return task
    except Exception as e:
        task.status = "failed"
        task.result = f"Worktree creation error: {e}"
        return task

    # Spawn claude CLI in background
    task.status = "running"
    task.updated_at = datetime.now(timezone.utc).isoformat()
    await _update_task_db(task, status="running")
    from app.relay import broadcast_event, KIND_AGENT_SPAWN
    asyncio.create_task(broadcast_event(KIND_AGENT_SPAWN, f"Agent {task_id} spawned: {prompt[:100]}", [["task_id", task_id], ["branch", branch]]))
    asyncio.create_task(_run_claude(task))

    return task


async def _run_claude(task: AgentTask) -> None:
    """Run claude CLI in the worktree and capture output."""
    try:
        # Check if claude CLI exists
        which_proc = await asyncio.create_subprocess_exec(
            "which", "claude",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await which_proc.communicate()

        if which_proc.returncode != 0:
            task.status = "failed"
            task.result = "claude CLI not found. Install Claude Code first."
            task.updated_at = datetime.now(timezone.utc).isoformat()
            return

        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", task.prompt,
            "--output-format", "text",
            "--max-turns", "5",
            "-y",
            cwd=task.worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        task.pid = proc.pid

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=300  # 5 min timeout
        )

        task.result = stdout.decode(errors="replace")[:5000]
        task.status = "done" if proc.returncode == 0 else "failed"
        if proc.returncode != 0 and stderr:
            task.result += f"\n\nSTDERR:\n{stderr.decode(errors='replace')[:1000]}"
    except asyncio.TimeoutError:
        task.status = "failed"
        task.result = "Agent timed out (5 min limit)"
    except Exception as e:
        task.status = "failed"
        task.result = str(e)
    finally:
        task.updated_at = datetime.now(timezone.utc).isoformat()
        task.diff_summary = await _capture_diff_summary(task)
        await _update_task_db(task, status=task.status, result=task.result, diff_summary=task.diff_summary)
        from app.relay import broadcast_event, KIND_AGENT_DONE, KIND_AGENT_FAILED
        kind = KIND_AGENT_DONE if task.status == "done" else KIND_AGENT_FAILED
        asyncio.create_task(broadcast_event(kind, f"Agent {task.id}: {task.result[:200]}", [["task_id", task.id]]))
        # Clean up worktree if no changes
        await _cleanup_worktree(task)


async def _cleanup_worktree(task: AgentTask) -> None:
    """Remove worktree if there are no commits beyond the branch point."""
    try:
        # Check if there are new commits on the branch
        proc = await asyncio.create_subprocess_exec(
            "git", "log", f"HEAD..{task.branch}", "--oneline",
            cwd=task.repo,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        if not stdout.decode().strip():
            # No new commits — safe to remove
            await asyncio.create_subprocess_exec(
                "git", "worktree", "remove", "--force", task.worktree_path,
                cwd=task.repo,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.create_subprocess_exec(
                "git", "branch", "-D", task.branch,
                cwd=task.repo,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info("worktree_cleaned", task_id=task.id)
    except Exception:
        logger.exception("worktree_cleanup_failed", task_id=task.id)


async def spawn_with_squad(prompt: str, repo: str = "~/Local_Dev") -> AgentTask:
    """Spawn an agent using claude-squad for TUI oversight.

    Falls back to direct claude CLI if claude-squad is not found.
    """
    # Check if claude-squad is available
    which_proc = await asyncio.create_subprocess_exec(
        "which", "claude-squad",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await which_proc.communicate()

    if which_proc.returncode != 0:
        logger.warning("claude_squad_not_found", fallback="direct_spawn")
        return await spawn_agent(prompt, repo)

    task_id = uuid.uuid4().hex[:12]
    repo_path = Path(repo).expanduser()
    session_name = f"squad-{task_id}"

    task = AgentTask(
        id=task_id,
        prompt=prompt,
        repo=str(repo_path),
        branch=session_name,
        worktree_path="",  # managed by claude-squad
    )
    _tasks[task_id] = task

    try:
        # Launch claude-squad in a detached tmux session
        proc = await asyncio.create_subprocess_exec(
            "tmux", "new-session", "-d", "-s", session_name,
            "claude-squad", "-p", "claude",
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            task.status = "failed"
            task.result = f"Failed to start squad session: {stderr.decode()}"
            return task

        task.status = "running"
        task.updated_at = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        task.status = "failed"
        task.result = str(e)

    return task


async def list_squad_sessions() -> list[dict]:
    """List active tmux sessions (claude-squad uses tmux under the hood)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "tmux", "list-sessions",
            "-F", "#{session_name}\t#{session_created}\t#{session_windows}\t#{session_attached}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return []

        sessions = []
        for line in stdout.decode().strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 4:
                sessions.append({
                    "name": parts[0],
                    "created": parts[1],
                    "windows": int(parts[2]),
                    "attached": parts[3] == "1",
                })
        return sessions
    except Exception:
        logger.exception("tmux_list_failed")
        return []


def get_task(task_id: str) -> AgentTask | None:
    if task_id in _tasks:
        return _tasks[task_id]
    from app.db import get_agent_task_sync
    row = get_agent_task_sync(task_id)
    return _task_from_row(row) if row else None


def list_tasks() -> list[dict]:
    from app.db import list_agent_tasks_sync
    rows = list_agent_tasks_sync()
    return [
        {"id": r["id"], "prompt": (r["prompt"] or "")[:100], "status": r["status"],
         "branch": r["branch"], "created_at": r["created_at"], "updated_at": r["updated_at"]}
        for r in rows
    ]
