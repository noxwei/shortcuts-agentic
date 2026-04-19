from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    GEMMA_BASE_URL: str = "http://127.0.0.1:5574"
    SHORTCUTS_AUTH_TOKEN: str | None = None
    DB_PATH: str = "~/.local/share/shortcuts-agentic/jobs.db"
    NTFY_TOPIC: str | None = None
    INFERENCE_BACKEND: str = "gemma"  # "gemma" or "ollama"
    OLLAMA_MODEL: str = "qwen3:14b"
    DAILY_CHAR_BUDGET: int = 500_000


settings = Settings()
