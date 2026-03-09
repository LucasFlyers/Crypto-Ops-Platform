"""
app/config.py
─────────────
Central configuration loaded from environment variables.
Uses pydantic-settings for type-safe, validated config.
All secrets come from env — never hardcoded.
"""

from functools import lru_cache
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="dev-secret-key")

    # ── PostgreSQL ───────────────────────────────────────────────
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="crypto_ops")
    postgres_user: str = Field(default="crypto_ops_user")
    postgres_password: str = Field(default="securepassword123")
    database_url: str = Field(
        default="postgresql+asyncpg://crypto_ops_user:securepassword123@localhost:5432/crypto_ops"
    )
    database_url_sync: str = Field(
        default="postgresql://crypto_ops_user:securepassword123@localhost:5432/crypto_ops"
    )

    def model_post_init(self, __context) -> None:
        """Auto-fix database URL prefixes after loading from env."""
        # Railway sets DATABASE_URL with plain postgresql:// — fix for asyncpg
        if self.database_url.startswith("postgresql://"):
            object.__setattr__(self, "database_url",
                self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1))
        # Ensure sync URL uses plain postgresql://
        if self.database_url_sync.startswith("postgresql+asyncpg://"):
            object.__setattr__(self, "database_url_sync",
                self.database_url_sync.replace("postgresql+asyncpg://", "postgresql://", 1))

    # ── Redis / Celery ───────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    # ── AI / LLM ─────────────────────────────────────────────────
    openai_api_key: str = Field(default="")
    ai_model: str = Field(default="gpt-4o")
    ai_max_tokens: int = Field(default=1024)
    ai_max_retries: int = Field(default=3)
    ai_timeout_seconds: int = Field(default=30)

    # ── Fraud Detection ──────────────────────────────────────────
    fraud_high_risk_threshold: float = Field(default=0.7)
    fraud_medium_risk_threshold: float = Field(default=0.4)
    fraud_flag_window_hours: int = Field(default=24)
    fraud_max_complaints_per_wallet: int = Field(default=3)
    fraud_max_failed_tx_per_wallet: int = Field(default=5)

    # ── Routing ──────────────────────────────────────────────────
    high_value_tx_threshold_usd: float = Field(default=10_000.0)

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @computed_field
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings singleton.
    Call get_settings() anywhere in the codebase — returns the same instance.
    """
    return Settings()


settings = get_settings()
