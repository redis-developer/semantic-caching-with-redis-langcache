from functools import lru_cache
from os import environ
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

load_dotenv()

AppEnv = Literal["development", "test", "production"]
LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


class Settings(BaseModel):
    app_env: AppEnv = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    port: int = Field(default=8080, validation_alias="PORT")
    redis_url: str = Field(
        default="redis://localhost:6379",
        min_length=1,
        validation_alias="REDIS_URL",
    )
    log_level: LogLevel = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_stream_key: str = Field(
        default="logs",
        min_length=1,
        validation_alias="LOG_STREAM_KEY",
    )
    langcache_ttl_seconds: int = Field(
        default=3600,
        gt=0,
        validation_alias="LANGCACHE_TTL_SECONDS",
    )
    langcache_cache_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        validation_alias="LANGCACHE_CACHE_THRESHOLD",
    )
    langcache_knowledge_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        validation_alias="LANGCACHE_KNOWLEDGE_THRESHOLD",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.model_validate(environ)
