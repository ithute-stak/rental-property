from fastapi.testclient import TestClient

from app.main import app


def test_empty_public_feed_and_typo_tolerant_search_are_available():
    with TestClient(app) as client:
        response = client.get("/api/v1/properties/feed")
        typo_response = client.get("/api/v1/properties/feed?q=Khubetswana")

    assert response.status_code == 200
    assert response.json() == []
    assert typo_response.status_code == 200
    assert typo_response.json() == []


def test_feed_rejects_incomplete_coordinates():
    with TestClient(app) as client:
        response = client.get("/api/v1/properties/feed?latitude=-29.31")

    assert response.status_code == 422
