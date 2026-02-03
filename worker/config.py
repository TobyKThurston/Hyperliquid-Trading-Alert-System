"""Worker configuration."""
from pydantic_settings import BaseSettings
from typing import List


class WorkerSettings(BaseSettings):
    """Worker settings."""

    database_url: str = "postgresql+asyncpg://pulse_user:pulse_password@localhost:5432/pulse_db"
    worker_id: str = "worker-1"
    hyperliquid_ws_url: str = "wss://api.hyperliquid.xyz/ws"
    hyperliquid_rest_url: str = "https://api.hyperliquid.xyz"
    symbols: str = "BTC,ETH"  # Comma-separated
    log_level: str = "INFO"
    retry_backoff_max: int = 5  # Max retry attempts
    retry_poll_interval: int = 30  # Seconds between retry polls

    @property
    def symbol_list(self) -> List[str]:
        """Parse symbols string into list."""
        return [s.strip().upper() for s in self.symbols.split(",") if s.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = WorkerSettings()

