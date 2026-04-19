"""Relay module tests — broadcast and subscribe."""

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.relay import (
    KIND_AGENT_DONE,
    KIND_AGENT_FAILED,
    KIND_AGENT_SPAWN,
    KIND_TASK_CREATED,
    KIND_TASK_UPDATED,
    KIND_TEAM_MESSAGE,
    broadcast_event,
    subscribe_events,
)


@patch("app.relay.httpx.AsyncClient")
async def test_broadcast_payload(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    await broadcast_event(KIND_AGENT_SPAWN, "Agent spawned", [["task_id", "abc"]])

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json") or call_args[0][1]
    assert payload["kind"] == KIND_AGENT_SPAWN
    assert payload["content"] == "Agent spawned"
    assert payload["pubkey"] == "shortcuts-agentic"


@patch("app.relay.httpx.AsyncClient")
async def test_broadcast_default_tags(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    await broadcast_event(KIND_AGENT_DONE, "Done")

    call_args = mock_client.post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json") or call_args[0][1]
    assert payload["tags"] == []


@patch("app.relay.httpx.AsyncClient")
async def test_broadcast_connection_error(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_client_cls.return_value = mock_client

    # Should not raise
    await broadcast_event(KIND_AGENT_SPAWN, "test")


@patch("app.relay.httpx.AsyncClient")
async def test_broadcast_http_error(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.raise_for_status = AsyncMock(
        side_effect=httpx.HTTPStatusError("error", request=AsyncMock(), response=mock_response)
    )
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    # Should not raise
    await broadcast_event(KIND_AGENT_FAILED, "failed")


def test_kinds_correct():
    assert KIND_AGENT_SPAWN == 1000
    assert KIND_AGENT_DONE == 1001
    assert KIND_AGENT_FAILED == 1002
    assert KIND_TEAM_MESSAGE == 1003
    assert KIND_TASK_CREATED == 1004
    assert KIND_TASK_UPDATED == 1005


@patch("app.relay.httpx.AsyncClient")
async def test_subscribe_returns_events(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: [{"id": "1", "kind": 1000, "content": "test"}]
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    events = await subscribe_events(kinds=[KIND_AGENT_SPAWN])
    assert len(events) == 1
    assert events[0]["kind"] == 1000


@patch("app.relay.httpx.AsyncClient")
async def test_subscribe_empty_kinds(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: []
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    events = await subscribe_events()
    assert events == []


@patch("app.relay.httpx.AsyncClient")
async def test_subscribe_swallows_errors(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=Exception("network down"))
    mock_client_cls.return_value = mock_client

    events = await subscribe_events()
    assert events == []
