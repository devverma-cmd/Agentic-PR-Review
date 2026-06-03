from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Groq
    groq_api_key: str = Field(..., description="Groq API key")

    # GitHub
    github_token: str = Field(..., description="GitHub PAT or installation token")
    github_webhook_secret: str = Field(..., description="Webhook HMAC secret")
    github_app_id: str | None = None
    github_app_private_key_path: str | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Review behaviour
    max_files_per_review: int = 20
    severity_threshold: str = "low"   # low | medium | high | critical
    summary_only: bool = False

    # Model — best Groq models for code review:
    #   "llama-3.3-70b-versatile"   (recommended — best quality)
    #   "llama-3.1-8b-instant"      (faster, lower cost)
    #   "moonshotai/kimi-k2-instruct" (strong at code)
    model_name: str = "llama-3.3-70b-versatile"
    max_tokens: int = 4096

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
