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
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_region: str = "us-east-1"
    object_storage_bucket: str = "rental-property"
    object_storage_access_key: str = "rental"
    object_storage_secret_key: str = "rental-development-secret"
    object_storage_public_base_url: str = "http://localhost:9000/rental-property"
    media_upload_expiry_seconds: int = 900
    object_storage_verify_uploads: bool = True
    maintenance_interval_seconds: int = 60
    maintenance_lock_seconds: int = 55
    viewing_reminder_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
