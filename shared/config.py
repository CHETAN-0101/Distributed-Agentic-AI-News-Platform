"""
AgentOS — Centralized configuration using pydantic-settings.
All services import from this module.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Platform
    # -------------------------------------------------------------------------
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    secret_key: str = Field(default="change-me", min_length=16)
    tenant_default: str = "default"

    # -------------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://agentos:agentos_dev_password@localhost:5432/agentos"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20

    # -------------------------------------------------------------------------
    # RabbitMQ
    # -------------------------------------------------------------------------
    rabbitmq_url: str = "amqp://agentos:agentos_dev_password@localhost:5672/"
    rabbitmq_prefetch_count: int = 10

    # -------------------------------------------------------------------------
    # LLM Provider
    # -------------------------------------------------------------------------
    llm_provider: Literal["mistral", "openai", "ollama"] = "mistral"

    # Mistral
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_max_tokens: int = 4096
    mistral_temperature: float = 0.1

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # Embeddings
    embedding_provider: Literal["mistral", "openai", "ollama"] = "mistral"
    embedding_model: str = "mistral-embed"
    embedding_dim: int = 1024

    # -------------------------------------------------------------------------
    # Service URLs
    # -------------------------------------------------------------------------
    api_gateway_url: str = "http://localhost:8000"
    agent_registry_url: str = "http://localhost:8001"
    orchestrator_url: str = "http://localhost:8002"
    workflow_service_url: str = "http://localhost:8003"
    memory_service_url: str = "http://localhost:8004"
    evidence_service_url: str = "http://localhost:8005"
    verification_service_url: str = "http://localhost:8006"
    policy_service_url: str = "http://localhost:8007"
    approval_service_url: str = "http://localhost:8008"
    evaluation_service_url: str = "http://localhost:8009"
    notification_service_url: str = "http://localhost:8010"

    # -------------------------------------------------------------------------
    # This service
    # -------------------------------------------------------------------------
    service_name: str = "agentos"
    service_port: int = 8000
    service_host: str = "0.0.0.0"

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_enabled: bool = True
    prometheus_port: int = 9090

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    rate_limit_per_minute: int = 60
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # -------------------------------------------------------------------------
    # News Ingestion
    # -------------------------------------------------------------------------
    news_ingestion_interval_seconds: int = 300
    gnews_api_key: str = ""
    newsdata_api_key: str = ""

    # -------------------------------------------------------------------------
    # Agent
    # -------------------------------------------------------------------------
    agent_id: str = ""
    agent_port: int = 9000
    agent_heartbeat_interval: int = 30

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Module-level singleton
settings = get_settings()
