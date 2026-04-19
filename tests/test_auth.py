"""Auth tests."""


async def test_bearer_token_auth(client, auth_headers):
    resp = await client.get("/v1/budget", headers=auth_headers)
    assert resp.status_code == 200


async def test_tailscale_header_auth(client, tailscale_headers):
    resp = await client.get("/v1/budget", headers=tailscale_headers)
    assert resp.status_code == 200


async def test_no_auth_rejected(client):
    resp = await client.get("/v1/budget")
    assert resp.status_code == 401


async def test_bad_bearer_token_rejected(client):
    resp = await client.get("/v1/budget", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


async def test_empty_bearer_rejected(client):
    resp = await client.get("/v1/budget", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


async def test_bearer_without_prefix_rejected(client):
    resp = await client.get("/v1/budget", headers={"Authorization": "test-token-12345"})
    assert resp.status_code == 401


async def test_tailscale_header_takes_priority(client):
    resp = await client.get("/v1/budget", headers={"Tailscale-User-Login": "user@ts", "Authorization": "Bearer bad"})
    assert resp.status_code == 200
