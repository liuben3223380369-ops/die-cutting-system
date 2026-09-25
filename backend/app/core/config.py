"""应用配置管理"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "模切流程系统"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production-use-long-random-string"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/die_cutting.db"

    # CORS — 开发前端 + 本机 EXE 同源场景；可用 CORS_ORIGINS 环境变量覆盖
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Logging
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in ("development", "dev", "local")


@lru_cache
def get_settings() -> Settings:
    return Settings()
