from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / 'trading_platform.db').as_posix()}"
VALID_APP_ENVS = {"development", "testing", "production"}
DEFAULT_DEV_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]
DEFAULT_TRUSTED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DEFAULT_UPLOAD_CONTENT_TYPES = [
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
]


class Settings(BaseSettings):
    app_name: str = "Trading Backtesting Platform"
    app_env: str = "development"
    debug: bool | None = Field(default=None)
    database_url: str = DEFAULT_DATABASE_URL
    data_dir: str = "data"
    log_level: str = "INFO"
    secret_key: str = "change-me"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    web_concurrency: int = Field(default=1, ge=1, le=8)
    json_logs: bool | None = Field(default=None)
    cors_allowed_origins: list[str] | None = None
    trusted_hosts: list[str] | None = None
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)
    allowed_upload_content_types: list[str] | None = None
    angel_api_key: str | None = None
    angel_client_id: str | None = None
    angel_mpin: str | None = None
    angel_totp_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: Any) -> str:
        normalized = str(value or "development").strip().lower()
        if normalized not in VALID_APP_ENVS:
            raise ValueError(f"app_env must be one of {sorted(VALID_APP_ENVS)}")
        return normalized

    @field_validator("debug", "json_logs", mode="before")
    @classmethod
    def parse_optional_bool(cls, value: Any) -> bool | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
                return False
        raise ValueError("value must be a boolean-compatible value")

    @field_validator("cors_allowed_origins", "trusted_hosts", "allowed_upload_content_types", mode="before")
    @classmethod
    def parse_list_values(cls, value: Any) -> list[str] | None:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            entries = [item.strip() for item in value.split(",")]
            return [item for item in entries if item]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError("value must be a comma-separated string or list")

    @field_validator("angel_api_key", "angel_client_id", "angel_mpin", "angel_totp_secret", mode="before")
    @classmethod
    def normalize_optional_secret_fields(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("host", mode="before")
    @classmethod
    def normalize_host(cls, value: Any) -> str:
        host = str(value or "127.0.0.1").strip()
        if not host:
            raise ValueError("host is required")
        return host

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: Any) -> str:
        normalized = str(value or "INFO").strip().upper()
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in valid_levels:
            raise ValueError(f"log_level must be one of {sorted(valid_levels)}")
        return normalized

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any) -> str:
        raw_value = str(value).strip() if value else DEFAULT_DATABASE_URL
        try:
            url = make_url(raw_value)
        except ArgumentError as exc:
            raise ValueError("database_url is not a valid SQLAlchemy URL") from exc

        if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
            database_path = Path(url.database)
            if not database_path.is_absolute():
                database_path = (PROJECT_ROOT / database_path).resolve()
            return f"sqlite:///{database_path.as_posix()}"

        return raw_value

    @model_validator(mode="after")
    def apply_environment_defaults(self):
        if self.debug is None:
            self.debug = self.app_env in {"development", "testing"}

        if self.json_logs is None:
            self.json_logs = self.app_env == "production"

        if self.cors_allowed_origins is None:
            self.cors_allowed_origins = DEFAULT_DEV_ORIGINS.copy() if self.app_env != "production" else []

        if self.trusted_hosts is None:
            self.trusted_hosts = DEFAULT_TRUSTED_HOSTS.copy()

        if self.allowed_upload_content_types is None:
            self.allowed_upload_content_types = DEFAULT_UPLOAD_CONTENT_TYPES.copy()

        if self.app_env == "production" and self.secret_key.strip() == "change-me":
            raise ValueError("secret_key must be changed for production")

        return self

    @computed_field
    @property
    def base_dir(self) -> Path:
        return PROJECT_ROOT

    @computed_field
    @property
    def templates_dir(self) -> Path:
        return self.base_dir / "app" / "templates"

    @computed_field
    @property
    def static_dir(self) -> Path:
        return self.base_dir / "app" / "static"

    @computed_field
    @property
    def data_path(self) -> Path:
        return self.base_dir / self.data_dir

    @computed_field
    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @computed_field
    @property
    def log_file_path(self) -> Path:
        return self.logs_dir / "app.log"

    @computed_field
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    env_file = os.getenv("SETTINGS_ENV_FILE")
    if env_file:
        return Settings(_env_file=Path(env_file))
    return Settings()
