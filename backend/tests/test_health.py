from fastapi.testclient import TestClient

from app.main import app


def test_liveness_and_readiness() -> None:
    with TestClient(app) as client:
        legacy = client.get("/api/v1/health")
        live = client.get("/api/v1/health/live")
        ready = client.get("/api/v1/health/ready")

    assert legacy.status_code == 200
    assert legacy.json() == {"status": "ok"}
    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
        },
    }
