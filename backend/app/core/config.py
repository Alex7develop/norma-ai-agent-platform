"""Environment-backed application configuration.

Keeping settings in one immutable object makes runtime dependencies explicit
and prevents infrastructure code from reading environment variables directly.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Norma AI"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-3.5-flash"
    llm_max_completion_tokens: int = 1_200
    database_url: str = "postgresql+asyncpg://norma:norma@localhost:5432/norma"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "norma_knowledge"
    redis_url: str = "redis://localhost:6379/0"
    launch_strategy_queue: str = "norma:jobs:launch_strategy"
    web_search_enabled: bool = True
    web_search_max_results: int = 5
    embedding_service_url: str = "http://localhost:8001"
    embedding_dimension: int = 1024
    max_upload_size_bytes: int = 10 * 1024 * 1024
    chunk_size: int = 2_500
    chunk_overlap: int = 300
    secret_key: SecretStr = SecretStr("change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "norma-ai"
    jwt_audience: str = "norma-ai-api"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    access_cookie_name: str = "norma_access"
    refresh_cookie_name: str = "norma_refresh"
    notion_client_id: str | None = None
    notion_client_secret: SecretStr | None = None
    notion_redirect_uri: str = (
        "http://localhost:8000/api/v1/integrations/notion/callback"
    )
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    """Return one settings instance per process."""

    return Settings()


settings = get_settings()
