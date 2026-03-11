"""
HealthOS application settings.

Loaded from environment variables with sensible defaults.
All settings are immutable after initialization.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────────
    app_name: str = "eminence-healthos"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://healthos:healthos@localhost:5432/healthos"
    database_sync_url: str = "postgresql://healthos:healthos@localhost:5432/healthos"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # ── Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_url: str = "redis://localhost:6379/1"
    redis_cache_ttl: int = 3600  # 1 hour default

    # ── Kafka ────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "healthos-agents"

    # ── Neo4j ────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "healthos-neo4j"

    # ── Qdrant ───────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"

    # ── LLM Providers ────────────────────────────────────────────────
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-6"

    # ── Auth ─────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    keycloak_url: Optional[str] = None
    keycloak_realm: str = "healthos"
    keycloak_client_id: str = "healthos-api"
    keycloak_client_secret: Optional[str] = None

    # ── Multi-Tenant ─────────────────────────────────────────────────
    default_tenant_id: str = "default"
    tenant_header: str = "X-Tenant-ID"

    # ── CORS ─────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # ── Observability ────────────────────────────────────────────────
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    langchain_api_key: Optional[str] = None
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_service_name: str = "healthos"

    # ── Encryption ───────────────────────────────────────────────────
    phi_encryption_key: str = "change-me-32-byte-key-for-aes256"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
