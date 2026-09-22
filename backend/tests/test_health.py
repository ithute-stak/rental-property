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


def test_readiness_checks_database_and_redis() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok", "redis": "ok"}
