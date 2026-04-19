"""Core API tests."""

from unittest.mock import AsyncMock, patch


async def test_status_endpoint(client, auth_headers):
    with patch("app.main.inference_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {"backend": "gemma", "ready": True}
        resp = await client.get("/v1/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["inference"]["backend"] == "gemma"
    assert "uptime" in data


async def test_budget_endpoint(client, auth_headers):
    resp = await client.get("/v1/budget", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "chars_used" in data
    assert data["chars_used"] == 0


async def test_intent_returns_202(client, auth_headers):
    with patch("app.main._run_intent", new_callable=AsyncMock):
        resp = await client.post("/v1/intent", json={"source": "test", "text": "hello"}, headers=auth_headers)
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert len(data["job_id"]) == 32


async def test_intent_with_conversation_id(client, auth_headers):
    with patch("app.main._run_intent", new_callable=AsyncMock):
        resp = await client.post("/v1/intent", json={"source": "test", "text": "hello", "conversation_id": "conv123"}, headers=auth_headers)
    assert resp.json()["conversation_id"] == "conv123"


async def test_job_status_queued(client, auth_headers):
    with patch("app.main._run_intent", new_callable=AsyncMock):
        intent_resp = await client.post("/v1/intent", json={"source": "test", "text": "hello"}, headers=auth_headers)
    job_id = intent_resp.json()["job_id"]
    resp = await client.get(f"/v1/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


async def test_job_not_found(client, auth_headers):
    resp = await client.get("/v1/jobs/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


async def test_intent_missing_fields(client, auth_headers):
    resp = await client.post("/v1/intent", json={}, headers=auth_headers)
    assert resp.status_code == 422


async def test_conversation_history_empty(client, auth_headers):
    resp = await client.get("/v1/conversations/nonexistent/history", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["messages"] == []
    assert data["count"] == 0


async def test_conversation_history_with_messages(client, auth_headers):
    from app.db import save_conversation
    messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    await save_conversation("conv-abc", messages)
    resp = await client.get("/v1/conversations/conv-abc/history", headers=auth_headers)
    assert resp.json()["count"] == 2


async def test_conversation_history_requires_auth(client):
    resp = await client.get("/v1/conversations/x/history")
    assert resp.status_code in (401, 403)


async def test_agents_list_empty(client, auth_headers):
    resp = await client.get("/v1/agents", headers=auth_headers)
    assert resp.status_code == 200


async def test_agent_not_found(client, auth_headers):
    resp = await client.get("/v1/agents/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


async def test_agent_detail_includes_diff_summary(client, auth_headers):
    from app.db import create_agent_task, update_agent_task
    await create_agent_task("test-agent-1", "test prompt", "/tmp", "branch-1", "/tmp/wt")
    await update_agent_task("test-agent-1", status="done", result="ok", diff_summary="1 file changed")
    resp = await client.get("/v1/agents/test-agent-1", headers=auth_headers)
    assert resp.status_code == 200
    assert "diff_summary" in resp.json()


async def test_agent_detail_diff_summary_nullable(client, auth_headers):
    from app.db import create_agent_task
    await create_agent_task("test-agent-2", "test", "/tmp", "branch-2", "/tmp/wt2")
    resp = await client.get("/v1/agents/test-agent-2", headers=auth_headers)
    assert resp.status_code == 200


async def test_dashboard_returns_all_sections(client, auth_headers):
    with patch("app.main.inference_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {"backend": "gemma", "ready": True}
        resp = await client.get("/v1/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "inference" in data
    assert "budget" in data
    assert "agents" in data
    assert "relay" in data
    assert "uptime" in data


async def test_dashboard_requires_auth(client):
    resp = await client.get("/v1/dashboard")
    assert resp.status_code in (401, 403)


async def test_job_stream_returns_sse(client, auth_headers):
    from app.db import create_job, update_job
    await create_job("stream-job", "conv1", "test", "hello")
    await update_job("stream-job", "done", "result text")
    resp = await client.get("/v1/jobs/stream-job/stream", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert "data:" in resp.text


async def test_job_stream_not_found(client, auth_headers):
    resp = await client.get("/v1/jobs/nope/stream", headers=auth_headers)
    assert resp.status_code == 404


async def test_job_stream_requires_auth(client):
    resp = await client.get("/v1/jobs/x/stream")
    assert resp.status_code in (401, 403)


async def test_job_result_includes_intent_and_confidence(client, auth_headers):
    import json
    from app.db import create_job, update_job
    result = json.dumps({"response": "answer", "intent": "question", "confidence": 1.0})
    await create_job("structured-job", "conv1", "test", "hello")
    await update_job("structured-job", "done", result)
    resp = await client.get("/v1/jobs/structured-job", headers=auth_headers)
    data = resp.json()
    assert data["intent"] == "question"
    assert data["confidence"] == 1.0
    assert data["result"] == "answer"


async def test_job_result_backward_compat_plain_text(client, auth_headers):
    from app.db import create_job, update_job
    await create_job("plain-job", "conv1", "test", "hello")
    await update_job("plain-job", "done", "plain text result")
    resp = await client.get("/v1/jobs/plain-job", headers=auth_headers)
    data = resp.json()
    assert data["result"] == "plain text result"
    assert data["intent"] is None
    assert data["confidence"] is None
