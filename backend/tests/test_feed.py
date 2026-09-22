from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_empty_public_feed_is_available():
    response = client.get("/api/v1/properties/feed")

    assert response.status_code == 200
    assert response.json() == []


def test_feed_rejects_incomplete_coordinates():
    response = client.get("/api/v1/properties/feed?latitude=-29.31")

    assert response.status_code == 422
