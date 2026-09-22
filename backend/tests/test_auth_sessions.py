import uuid

from fastapi.testclient import TestClient

from app.main import app


def _register_and_login(client: TestClient) -> dict:
    phone = f"+2665{uuid.uuid4().int % 100000000:08d}"
    password = "MosalaSession123!"
    register = client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "display_name": "Session Test User",
            "password": password,
            "role": "house_seeker",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": phone, "password": password},
    )
    assert login.status_code == 200
    return login.json()


def test_refresh_token_rotates_and_reuse_revokes_family():
    with TestClient(app) as client:
        session = _register_and_login(client)
        old_refresh = session["refresh_token"]

        rotated = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert rotated.status_code == 200
        new_refresh = rotated.json()["refresh_token"]
        assert new_refresh != old_refresh
        assert rotated.json()["access_token"]

        replay = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert replay.status_code == 401
        assert "reuse" in replay.json()["detail"].lower()

        replacement_after_replay = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh},
        )
        assert replacement_after_replay.status_code == 401


def test_logout_revokes_refresh_session():
    with TestClient(app) as client:
        session = _register_and_login(client)
        refresh_token = session["refresh_token"]

        logout = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert logout.status_code == 204

        refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh.status_code == 401


def test_logout_all_revokes_every_device_session():
    with TestClient(app) as client:
        first = _register_and_login(client)
        user_phone = first["user"]["phone"]

        second_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": user_phone, "password": "MosalaSession123!"},
        )
        assert second_login.status_code == 200
        second = second_login.json()

        logout_all = client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {first['access_token']}"},
        )
        assert logout_all.status_code == 204

        first_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first["refresh_token"]},
        )
        second_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": second["refresh_token"]},
        )
        assert first_refresh.status_code == 401
        assert second_refresh.status_code == 401
