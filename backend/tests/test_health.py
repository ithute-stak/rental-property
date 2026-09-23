from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_exposes_release_identity() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": settings.app_version,
        "release": settings.release_sha,
    }


def test_readiness_checks_database_redis_and_object_storage() -> None:
    with patch("app.api.routes.health.storage.check_ready", return_value=None) as storage_ready:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "redis": "ok",
        "object_storage": "ok",
    }
    storage_ready.assert_called_once_with()


def test_readiness_returns_503_when_object_storage_is_unavailable() -> None:
    with patch(
        "app.api.routes.health.storage.check_ready",
        side_effect=RuntimeError("storage unavailable"),
    ):
        with TestClient(app) as client:
            response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service dependencies are not ready"}
