"""shortcuts-agentic: iOS Shortcuts -> Tailscale -> Mac Mini agentic backend."""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from app.audit import get_recent_logs, init_audit_table, log_request
from app.auth import verify_auth
from app.budget import budget_summary, init_usage_table
from app.db import create_job, get_job, init_db, load_conversation, update_job
from app.graph import run_graph
from app.inference import health as inference_health
from app.logging_config import setup_logging
from app.notify import push_result
from app.ratelimit import require_rate_limit
from app.relay import subscribe_events
from app.summarize import summarize_swarm
from app.swarm import get_task, list_squad_sessions, list_tasks, spawn_agent, spawn_with_squad
from app.teammate import (
    create_task as create_teammate_task,
    list_tasks as list_teammate_tasks,
    read_inbox,
    send_message,
    update_task_status,
)

_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time
    _start_time = time.time()
    setup_logging()
    await init_db()
    await init_usage_table()
    await init_audit_table()
    yield


app = FastAPI(title="shortcuts-agentic", lifespan=lifespan)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = ""
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                raw = await request.body()
                body = raw.decode(errors="replace")[:200]
            except Exception:
                pass
        response = await call_next(request)
        user = request.headers.get("Tailscale-User-Login") or "anonymous"
        asyncio.create_task(log_request(user, request.method, str(request.url.path), response.status_code, body))
        return response


app.add_middleware(AuditMiddleware)


# --- Models ---


class IntentRequest(BaseModel):
    source: str
    text: str
    conversation_id: str | None = None
    timestamp: str | None = None


class IntentResponse(BaseModel):
    job_id: str
    conversation_id: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    result: str | None
    intent: str | None = None
    confidence: float | None = None
    created_at: str
    updated_at: str


class SpawnRequest(BaseModel):
    prompt: str
    repo: str | None = None


class SummarizeRequest(BaseModel):
    task_ids: list[str] | None = None


class TeamMessageRequest(BaseModel):
    team: str
    agent: str
    message: str
    sender: str = "shortcuts-agentic"


class TeamTaskRequest(BaseModel):
    title: str
    description: str
    assigned_to: str = ""


class TaskStatusUpdate(BaseModel):
    status: str


# --- Routes ---


@app.get("/v1/status")
async def status(_user: str = Depends(verify_auth)):
    backend = await inference_health()
    return {
        "status": "ok",
        "inference": backend,
        "uptime": round(time.time() - _start_time, 1),
    }


async def _run_intent(job_id: str, text: str, conversation_id: str) -> None:
    """Background task: route intent, generate response via graph, store result."""
    try:
        await update_job(job_id, "running")
        result = await run_graph(conversation_id, text)
        await update_job(job_id, "done", json.dumps(result))
        response_text = result["response"] if isinstance(result, dict) else result
        await push_result(job_id, response_text, conversation_id)
    except Exception as exc:
        error_msg = str(exc)
        await update_job(job_id, "failed", error_msg)
        await push_result(job_id, f"FAILED: {error_msg}", conversation_id)


@app.post("/v1/intent", status_code=202)
async def intent(
    req: IntentRequest,
    background_tasks: BackgroundTasks,
    _user: str = Depends(require_rate_limit),
) -> IntentResponse:
    job_id = uuid.uuid4().hex
    conversation_id = req.conversation_id or uuid.uuid4().hex

    await create_job(job_id, conversation_id, req.source, req.text)
    background_tasks.add_task(_run_intent, job_id, req.text, conversation_id)

    return IntentResponse(job_id=job_id, conversation_id=conversation_id)


@app.get("/v1/jobs/{job_id}")
async def job_status(job_id: str, _user: str = Depends(verify_auth)) -> JobResponse:
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    result = job["result"]
    intent = None
    confidence = None
    if result:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "response" in parsed:
                result = parsed["response"]
                intent = parsed.get("intent")
                confidence = parsed.get("confidence")
        except (json.JSONDecodeError, TypeError):
            pass
    return JobResponse(
        job_id=job["id"], status=job["status"], result=result,
        intent=intent, confidence=confidence,
        created_at=job["created_at"], updated_at=job["updated_at"],
    )


# --- Budget endpoint (X-3) ---


@app.get("/v1/budget")
async def budget(_user: str = Depends(verify_auth)):
    return await budget_summary()


# --- Conversation history ---


@app.get("/v1/conversations/{conversation_id}/history")
async def conversation_history(conversation_id: str, _user: str = Depends(verify_auth)):
    messages = await load_conversation(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages, "count": len(messages)}


# --- Dashboard ---


@app.get("/v1/dashboard")
async def dashboard(_user: str = Depends(verify_auth)):
    backend = await inference_health()
    budget_data = await budget_summary()
    agents = list_tasks()
    active = sum(1 for a in agents if a.get("status") == "running")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            relay_resp = await client.get("http://127.0.0.1:8201/health")
            relay_data = relay_resp.json()
    except Exception:
        relay_data = {"ready": False}
    return {
        "inference": backend,
        "budget": budget_data,
        "agents": {"active_count": active, "total": len(agents)},
        "relay": relay_data,
        "uptime": round(time.time() - _start_time, 1),
    }


# --- Audit ---


@app.get("/v1/audit")
async def audit(_user: str = Depends(verify_auth)):
    logs = await get_recent_logs()
    return {"entries": logs, "count": len(logs)}


# --- Relay events proxy ---


@app.get("/v1/relay/events")
async def relay_events(kind: int | None = None, limit: int = 50, since: int = 0, _user: str = Depends(verify_auth)):
    kinds = [kind] if kind is not None else None
    events = await subscribe_events(kinds, since)
    return {"events": events[:limit], "count": len(events)}


# --- SSE streaming ---


@app.get("/v1/jobs/{job_id}/stream")
async def job_stream(job_id: str, _user: str = Depends(verify_auth)):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        import asyncio as aio
        for _ in range(30):
            j = await get_job(job_id)
            data = json.dumps({"status": j["status"], "result": j["result"]})
            yield f"data: {data}\n\n"
            if j["status"] in ("done", "failed"):
                return
            await aio.sleep(1)
        yield f"data: {json.dumps({'status': 'timeout', 'result': None})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- Agent swarm endpoints (M-2 / M-3 / M-4) ---


@app.post("/v1/agents/spawn", status_code=202)
async def spawn_agent_endpoint(req: SpawnRequest, _user=Depends(verify_auth)):
    """Spawn a claude CLI agent in a worktree."""
    task = await spawn_agent(req.prompt, req.repo or "~/Local_Dev")
    return {"task_id": task.id, "status": task.status, "branch": task.branch}


@app.post("/v1/agents/spawn-squad", status_code=202)
async def spawn_squad_endpoint(req: SpawnRequest, _user=Depends(verify_auth)):
    """Spawn a claude agent via claude-squad for TUI oversight."""
    task = await spawn_with_squad(req.prompt, req.repo or "~/Local_Dev")
    return {"task_id": task.id, "status": task.status, "branch": task.branch}


@app.get("/v1/agents/sessions")
async def squad_sessions(_user=Depends(verify_auth)):
    """List active claude-squad tmux sessions."""
    sessions = await list_squad_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@app.get("/v1/agents")
async def list_agents(_user=Depends(verify_auth)):
    """List all agent tasks."""
    return {"agents": list_tasks()}


@app.get("/v1/agents/{task_id}")
async def get_agent(task_id: str, _user=Depends(verify_auth)):
    """Get agent task status and result."""
    task = get_task(task_id)
    if task is None:
        raise HTTPException(404, "Agent task not found")
    return {
        "id": task.id, "prompt": task.prompt, "status": task.status,
        "branch": task.branch, "result": task.result,
        "diff_summary": task.diff_summary,
        "worktree_path": task.worktree_path,
        "created_at": task.created_at, "updated_at": task.updated_at,
    }


# --- Swarm summarization (M-6) ---


@app.post("/v1/agents/summarize")
async def summarize_agents(req: SummarizeRequest, _user=Depends(verify_auth)):
    """Summarize completed agent task results into one notification."""
    summary = await summarize_swarm(req.task_ids)
    return {"summary": summary}


# --- TeammateTool endpoints (M-5) ---


@app.post("/v1/team/message")
async def team_send_message(req: TeamMessageRequest, _user=Depends(verify_auth)):
    """Send a message to an agent's inbox."""
    msg = await send_message(req.team, req.agent, req.message, req.sender)
    return msg


@app.get("/v1/team/inbox/{team}/{agent}")
async def team_inbox(team: str, agent: str, _user=Depends(verify_auth)):
    """Read all messages in an agent's inbox."""
    return {"messages": await read_inbox(team, agent)}


@app.post("/v1/team/tasks")
async def team_create_task(req: TeamTaskRequest, _user=Depends(verify_auth)):
    """Create a shared task."""
    return await create_teammate_task(req.title, req.description, req.assigned_to)


@app.get("/v1/team/tasks")
async def team_list_tasks(_user=Depends(verify_auth)):
    """List all shared tasks."""
    return {"tasks": await list_teammate_tasks()}


@app.patch("/v1/team/tasks/{task_id}")
async def team_update_task(
    task_id: str, req: TaskStatusUpdate, _user=Depends(verify_auth)
):
    """Update a task's status."""
    task = await update_task_status(task_id, req.status)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task
