"""API configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Tolerate unrelated keys in shared .env files
    )

    api_key: str = "default-api-key-change-me"  # Admin/legacy env-var key — bypasses DB lookup
    admin_rate_limit_per_minute: int = 1000  # Admin-key rate limit ceiling
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+asyncpg://pulse_user:pulse_password@localhost:5432/pulse_db"
    redis_url: str = ""  # Empty disables rate limiting (fails open)
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"  # comma-separated

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
