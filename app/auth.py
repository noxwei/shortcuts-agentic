from fastapi import HTTPException, Request

from app.config import settings


async def verify_auth(request: Request) -> str:
    # Tailscale identity header (set by Tailscale when proxying)
    ts_user = request.headers.get("Tailscale-User-Login")
    if ts_user:
        return ts_user

    # Fallback: Bearer token auth
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and settings.SHORTCUTS_AUTH_TOKEN:
        token = auth_header.removeprefix("Bearer ").strip()
        if token == settings.SHORTCUTS_AUTH_TOKEN:
            return f"token:{token[:8]}..."

    raise HTTPException(status_code=401, detail="Unauthorized")
