import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionFactory, engine
from app.main import app
from app.provision_admin import provision_admin, validate_admin_inputs


def test_admin_provision_requires_supported_password_length():
    with pytest.raises(ValueError, match="8 characters"):
        validate_admin_inputs("59000000", "Mosala Admin", "short")


def test_admin_provision_normalizes_basic_identity_fields():
    phone, name = validate_admin_inputs(
        " 59000000 ",
        " Mosala Admin ",
        "StrongAdminPass123!",
    )

    assert phone == "59000000"
    assert name == "Mosala Admin"


def test_admin_provision_allows_email_only_identity():
    phone, name = validate_admin_inputs(
        None,
        " Mosala Admin ",
        "Bootstrap9!",
    )

    assert phone is None
    assert name == "Mosala Admin"


async def _bootstrap_email_admin(email: str, password: str) -> None:
    async with SessionFactory() as db:
        user = await provision_admin(
            db,
            phone=None,
            email=email,
            display_name="Production Owner",
            password=password,
        )
        assert user.phone is None
        assert user.email == email
        assert user.role == "admin"
    await engine.dispose()


def test_email_only_admin_can_login_through_real_auth_endpoint():
    email = f"owner-{uuid.uuid4().hex[:12]}@example.test"
    password = "Bootstrap9!"
    asyncio.run(_bootstrap_email_admin(email, password))

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"identifier": email, "password": password},
        )

        assert login.status_code == 200, login.text
        payload = login.json()
        assert payload["user"]["email"] == email
        assert payload["user"]["phone"] is None
        assert payload["user"]["role"] == "admin"
        assert payload["access_token"]
        assert payload["refresh_token"]
