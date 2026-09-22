import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_auth_secret():
    with pytest.raises(ValidationError):
        Settings(app_env="production", _env_file=None)


def test_production_accepts_explicit_secrets():
    settings = Settings(
        app_env="production",
        auth_secret_key="x" * 32,
        object_storage_secret_key="production-storage-secret",
        cors_origins="https://rentals.example.com",
        _env_file=None,
    )

    assert settings.maintenance_lock_seconds == 300
    assert settings.cors_origin_list == ["https://rentals.example.com"]


def test_cors_rejects_wildcard_with_credentials():
    with pytest.raises(ValidationError):
        Settings(cors_origins="*", _env_file=None)
