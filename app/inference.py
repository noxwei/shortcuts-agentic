"""Inference client — abstracts over Gemma MLX (port 5574) and Ollama."""

import httpx

from app.config import settings


async def chat(messages: list[dict], max_tokens: int = 500) -> str:
    """Send messages to the configured inference backend, return assistant content."""
    if settings.INFERENCE_BACKEND == "gemma":
        return await _chat_gemma(messages, max_tokens)
    return await _chat_ollama(messages, max_tokens)


async def _chat_gemma(messages: list[dict], max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.GEMMA_BASE_URL}/v1/chat",
            json={"messages": messages, "max_tokens": max_tokens},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def _chat_ollama(messages: list[dict], max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def health() -> dict:
    """Check inference backend health."""
    try:
        if settings.INFERENCE_BACKEND == "gemma":
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.GEMMA_BASE_URL}/health")
                data = resp.json()
                return {"backend": "gemma", "model": data.get("model"), "ready": data.get("model_ready", False)}
        else:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"backend": "ollama", "models": models, "ready": True}
    except httpx.HTTPError:
        return {"backend": settings.INFERENCE_BACKEND, "ready": False}
