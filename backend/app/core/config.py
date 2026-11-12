import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"  # development | production | test
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "http://localhost:5180,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5180"

    # Security & Administration
    ADMIN_API_KEY: str = ""  # Mandatory in production unless PUBLIC_DEMO_MODE=True
    PUBLIC_DEMO_MODE: bool = False  # If True, enables safe public demo with controlled mutations
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120
    RATE_LIMIT_SENSITIVE_PER_MINUTE: int = 20

    # Gemini LLM Provider (Google Gen AI SDK)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_TIMEOUT_SECONDS: float = 15.0

    # Database (PostgreSQL for production, SQLite for local standalone demo)
    DATABASE_URL: str = "sqlite+aiosqlite:///./wingman.db"

    # Observability
    PROMETHEUS_URL: str = "http://localhost:9090"
    LOKI_URL: str = "http://localhost:3100"
    TEMPO_URL: str = "http://localhost:3200"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # Vector DB / Embeddings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_STORAGE_PATH: str = "./qdrant_storage"

    # MLflow
    MLFLOW_TRACKING_URI: str = "./mlruns"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
