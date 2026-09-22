from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Rental Property API"
    app_version: str = "0.1.0"
    release_sha: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://rental:rental@localhost:5432/rental_property"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    booking_hold_seconds: int = 600
    auth_secret_key: str = "change-this-secret-before-production"
    auth_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 30
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 300
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_region: str = "us-east-1"
    object_storage_bucket: str = "rental-property"
    object_storage_access_key: str = "rental"
    object_storage_secret_key: str = "rental-development-secret"
    object_storage_public_base_url: str = "http://localhost:9000/rental-property"
    media_upload_expiry_seconds: int = 900
    object_storage_verify_uploads: bool = True
    maintenance_interval_seconds: int = 60
    maintenance_lock_seconds: int = 300
    viewing_reminder_hours: int = 24
    notification_relay_interval_seconds: float = 1.0
    notification_relay_batch_size: int = 100
    websocket_auth_timeout_seconds: int = 10
    websocket_heartbeat_seconds: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_runtime_safety(self):
        origins = self.cors_origin_list
        if "*" in origins:
            raise ValueError("CORS_ORIGINS cannot use '*' when authenticated requests are enabled")
        if self.access_token_minutes <= 0 or self.refresh_token_days <= 0:
            raise ValueError("Authentication token lifetimes must be positive")
        if self.login_rate_limit_attempts <= 0 or self.login_rate_limit_window_seconds <= 0:
            raise ValueError("Login rate-limit settings must be positive")
        if self.notification_relay_interval_seconds <= 0 or self.notification_relay_batch_size <= 0:
            raise ValueError("Realtime notification relay settings must be positive")
        if self.websocket_auth_timeout_seconds <= 0 or self.websocket_heartbeat_seconds <= 0:
            raise ValueError("WebSocket timing settings must be positive")

        if self.app_env.strip().lower() == "production":
            if (
                self.auth_secret_key == "change-this-secret-before-production"
                or len(self.auth_secret_key) < 32
            ):
                raise ValueError(
                    "AUTH_SECRET_KEY must be replaced with a strong production secret of at least 32 characters"
                )
            if self.object_storage_secret_key == "rental-development-secret":
                raise ValueError(
                    "OBJECT_STORAGE_SECRET_KEY must be replaced before production startup"
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
