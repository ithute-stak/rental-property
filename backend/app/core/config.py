from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Rental Property API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://rental:rental@localhost:5432/rental_property"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    booking_hold_seconds: int = 600
    auth_secret_key: str = "change-this-secret-before-production"
    auth_algorithm: str = "HS256"
    access_token_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
