import re

from fastapi.testclient import TestClient

from app.main import app


_SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
}


def test_request_id_and_security_headers_are_added() -> None:
    request_id = "mosala-test-request-1234"
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": request_id},
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id
    for name, expected in _SECURITY_HEADERS.items():
        assert response.headers[name] == expected


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "bad request id with spaces"},
        )

    generated = response.headers["x-request-id"]
    assert generated != "bad request id with spaces"
    assert re.fullmatch(r"[0-9a-f]{32}", generated)


def test_cors_preflight_also_gets_request_context_headers() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    assert response.headers["x-content-type-options"] == "nosniff"
