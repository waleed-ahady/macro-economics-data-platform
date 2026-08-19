from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Macro Economics Data Platform"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./macro_data.db"

    world_bank_base_url: str = "https://api.worldbank.org/v2"
    world_bank_config_path: Path = Path("configs/world_bank.yml")
    world_bank_lookback_years: int = Field(default=5, ge=1, le=20)

    request_timeout_seconds: float = Field(default=30.0, gt=0)
    api_base_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
