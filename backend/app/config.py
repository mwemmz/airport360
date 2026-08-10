from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Airport360"
    api_v1_prefix: str = "/v1"
    debug: bool = False

    secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Bootstrapping credentials (seed only, never used in prod)
    seed_admin_email: str = "admin@airport360.local"
    seed_admin_password: str = "Admin123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
