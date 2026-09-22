import asyncio
import uuid

from fastapi.testclient import TestClient

from app.core.database import SessionFactory, engine
from app.main import app
from app.provision_admin import provision_admin


def _phone() -> str:
    return f"+266{uuid.uuid4().int % 100_000_000:08d}"


def _auth(token: str, **extra: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", **extra}


async def _bootstrap_admin(phone: str, password: str) -> None:
    async with SessionFactory() as db:
        await provision_admin(
            db,
            phone=phone,
            display_name="Audit HTTP Admin",
            password=password,
        )
    await engine.dispose()


def test_admin_action_is_queryable_by_request_id() -> None:
    suffix = uuid.uuid4().hex[:10]
    admin_phone = _phone()
    admin_password = "MosalaAuditAdmin123!"
    asyncio.run(_bootstrap_admin(admin_phone, admin_password))

    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": admin_phone, "password": admin_password},
        )
        assert admin_login.status_code == 200, admin_login.text
        admin_session = admin_login.json()
        admin_token = admin_session["access_token"]
        admin_id = admin_session["user"]["id"]

        landlord_phone = _phone()
        landlord_password = "MosalaAuditLandlord123!"
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "phone": landlord_phone,
                "display_name": f"Audit Landlord {suffix}",
                "password": landlord_password,
                "role": "landlord",
            },
        )
        assert registered.status_code == 201, registered.text
        landlord_id = registered.json()["id"]

        landlord_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": landlord_phone, "password": landlord_password},
        )
        assert landlord_login.status_code == 200, landlord_login.text
        landlord_token = landlord_login.json()["access_token"]

        profile = client.put(
            "/api/v1/landlords/me",
            headers=_auth(landlord_token),
            json={
                "business_name": f"Audit Rentals {suffix}",
                "physical_address": "Maseru",
            },
        )
        assert profile.status_code == 200, profile.text
        profile_id = profile.json()["id"]

        submitted = client.post(
            "/api/v1/landlords/me/submit",
            headers=_auth(landlord_token),
        )
        assert submitted.status_code == 200, submitted.text

        request_id = f"audit-http-{suffix}"
        decided = client.patch(
            f"/api/v1/admin/landlords/{landlord_id}/verification",
            headers=_auth(admin_token, **{"X-Request-ID": request_id}),
            json={"approved": True},
        )
        assert decided.status_code == 200, decided.text
        assert decided.headers["x-request-id"] == request_id

        audit = client.get(
            "/api/v1/admin/audit",
            headers=_auth(admin_token),
            params={
                "action": "landlord.verification.approved",
                "entity_type": "landlord_profile",
                "entity_id": profile_id,
            },
        )
        assert audit.status_code == 200, audit.text
        events = audit.json()
        assert len(events) == 1
        event = events[0]
        assert event["actor_id"] == admin_id
        assert event["actor_role"] == "admin"
        assert event["request_id"] == request_id
        assert event["details"]["user_id"] == landlord_id
        assert event["details"]["from_status"] == "pending"
        assert event["details"]["to_status"] == "approved"

        forbidden = client.get(
            "/api/v1/admin/audit",
            headers=_auth(landlord_token),
        )
        assert forbidden.status_code == 403
