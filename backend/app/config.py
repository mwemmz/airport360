from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Airport360"
    api_v1_prefix: str = "/v1"
    debug: bool = False

    database_url: str = "sqlite:///./airport360.db"
    turso_auth_token: str = ""
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Bootstrapping credentials (seed only, never used in prod)
    seed_admin_email: str = "admin@airport360.local"
    seed_admin_password: str = "Admin123!"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Turso's dashboard shows `libsql://host`; the sqlalchemy-libsql dialect
        registers as `sqlite.libsql`, so the URL must use the `sqlite+libsql` scheme."""
        if v.startswith("libsql://") and not v.startswith("sqlite+libsql://"):
            base = v.replace("libsql://", "sqlite+libsql://", 1)
            return base if "?" in base else f"{base}?secure=true"
        return v

    @property
    def engine_connect_args(self) -> dict[str, Any]:
        """libSQL (Turso) uses the sqlalchemy-libsql driver with an auth token;
        local SQLite needs check_same_thread disabled for the threaded server."""
        if self.database_url.startswith("sqlite+libsql"):
            return {"auth_token": self.turso_auth_token} if self.turso_auth_token else {}
        if self.database_url.startswith("sqlite"):
            return {"check_same_thread": False}
        return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
