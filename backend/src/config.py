import os
from functools import lru_cache

from pydantic import BaseModel, ValidationError, field_validator


class Settings(BaseModel):
    env: str = "dev"
    frontend_origin: str | None = None
    api_auth_token: str
    log_level: str = "INFO"
    update_interval_seconds: int = 30

    @field_validator("env")
    @classmethod
    def validate_env(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"dev", "prod"}:
            raise ValueError("ENV must be either 'dev' or 'prod'")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        return value.upper().strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        settings = Settings(
            env=os.getenv("ENV", "dev"),
            frontend_origin=os.getenv("FRONTEND_ORIGIN"),
            api_auth_token=os.getenv("API_AUTH_TOKEN", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            update_interval_seconds=int(os.getenv("UPDATE_INTERVAL_SECONDS", "30")),
        )
    except ValidationError as error:
        raise ValueError(f"Invalid configuration: {error}") from error

    if not settings.api_auth_token:
        raise ValueError("API_AUTH_TOKEN must be set")

    if settings.env == "prod" and not settings.frontend_origin:
        raise ValueError("FRONTEND_ORIGIN must be set when ENV=prod")

    return settings
