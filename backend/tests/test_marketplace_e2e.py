import asyncio
import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionFactory, engine
from app.core.security import hash_password
from app.main import app
from app.models.rental import User, UserRole


PASSWORD = "MosalaAcceptance123!"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _unique_phone(prefix: str) -> str:
    return f"+266{prefix}{uuid.uuid4().int % 10_000_000:07d}"


async def _bootstrap_admin(phone: str) -> None:
    async with SessionFactory() as db:
        existing = await db.scalar(select(User).where(User.phone == phone))
        if existing is None:
            db.add(
                User(
                    phone=phone,
                    display_name="Mosala Acceptance Admin",
                    role=UserRole.ADMIN.value,
                    hashed_password=hash_password(PASSWORD),
                    is_active=True,
                )
            )
            await db.commit()
    # TestClient runs the ASGI app on its own event loop. Dispose bootstrap
    # connections so asyncpg does not carry a pooled connection across loops.
    await engine.dispose()


def _register_and_login(
    client: TestClient,
    *,
    phone: str,
    name: str,
    role: str,
) -> tuple[str, dict]:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "display_name": name,
            "password": PASSWORD,
            "role": role,
        },
    )
    assert registered.status_code == 201, registered.text

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"identifier": phone, "password": PASSWORD},
    )
    assert logged_in.status_code == 200, logged_in.text
    body = logged_in.json()
    return body["access_token"], body["user"]


def test_complete_paid_advert_booking_and_tenancy_lifecycle() -> None:
    run_id = uuid.uuid4().hex[:10]
    admin_phone = _unique_phone("6")
    landlord_phone = _unique_phone("5")
    seeker_phone = _unique_phone("4")
    asyncio.run(_bootstrap_admin(admin_phone))

    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": admin_phone, "password": PASSWORD},
        )
        assert admin_login.status_code == 200, admin_login.text
        admin_token = admin_login.json()["access_token"]

        landlord_token, landlord = _register_and_login(
            client,
            phone=landlord_phone,
            name="Acceptance Landlord",
            role="landlord",
        )
        seeker_token, seeker = _register_and_login(
            client,
            phone=seeker_phone,
            name="Acceptance House Seeker",
            role="house_seeker",
        )

        # 1. Landlord onboarding and Mosala verification.
        profile = client.put(
            "/api/v1/landlords/me",
            headers=_headers(landlord_token),
            json={
                "business_name": "Acceptance Rentals",
                "physical_address": "Maseru, Lesotho",
            },
        )
        assert profile.status_code == 200, profile.text

        submitted_profile = client.post(
            "/api/v1/landlords/me/submit",
            headers=_headers(landlord_token),
        )
        assert submitted_profile.status_code == 200, submitted_profile.text
        assert submitted_profile.json()["verification_status"] == "pending"

        approve_landlord = client.patch(
            f"/api/v1/admin/landlords/{landlord['id']}/verification",
            headers=_headers(admin_token),
            json={"approved": True},
        )
        assert approve_landlord.status_code == 200, approve_landlord.text
        assert approve_landlord.json()["verification_status"] == "approved"

        # 2. Landlord creates a property and rentable unit, then submits it.
        created_property = client.post(
            "/api/v1/properties",
            headers=_headers(landlord_token),
            json={
                "title": f"Acceptance Home {run_id}",
                "description": "End-to-end acceptance property",
                "property_type": "house",
                "physical_address": "Exact Acceptance Street, Maseru",
                "district": "Maseru",
                "town": "Maseru",
                "area": "Maseru Central",
                "latitude": "-29.3151",
                "longitude": "27.4869",
                "total_rooms": 1,
                "security_level": "high",
                "security_features": {"gate": True, "lighting": True},
            },
        )
        assert created_property.status_code == 201, created_property.text
        property_id = created_property.json()["id"]

        created_unit = client.post(
            f"/api/v1/properties/{property_id}/units",
            headers=_headers(landlord_token),
            json={
                "name": "Room 1",
                "monthly_rent": "2500.00",
                "deposit": "1000.00",
            },
        )
        assert created_unit.status_code == 201, created_unit.text
        unit_id = created_unit.json()["id"]

        property_submission = client.post(
            f"/api/v1/properties/{property_id}/submit",
            headers=_headers(landlord_token),
        )
        assert property_submission.status_code == 200, property_submission.text
        assert property_submission.json()["status"] == "pending_verification"

        # 3. Mosala approves the advert and completes the advertising-payment lifecycle.
        property_approval = client.post(
            f"/api/v1/admin/properties/{property_id}/approve",
            headers=_headers(admin_token),
        )
        assert property_approval.status_code == 200, property_approval.text
        assert property_approval.json()["status"] == "approved"

        charge_quote = client.put(
            f"/api/v1/admin/properties/{property_id}/charge",
            headers=_headers(admin_token),
            json={"amount": "75.00", "note": "Acceptance advert fee", "waive": False},
        )
        assert charge_quote.status_code == 200, charge_quote.text
        assert charge_quote.json()["status"] == "quoted"

        advert_payment = client.post(
            f"/api/v1/advertising/properties/{property_id}/charge/payment",
            headers=_headers(landlord_token),
            json={"method": "mobile_money", "reference": f"ADV-{run_id}"},
        )
        assert advert_payment.status_code == 200, advert_payment.text
        assert advert_payment.json()["status"] == "payment_submitted"

        advert_confirm = client.post(
            f"/api/v1/admin/properties/{property_id}/charge/confirm",
            headers=_headers(admin_token),
            json={"note": "Acceptance advert payment verified"},
        )
        assert advert_confirm.status_code == 200, advert_confirm.text
        assert advert_confirm.json()["status"] == "paid"

        activation = client.post(
            f"/api/v1/admin/properties/{property_id}/activate",
            headers=_headers(admin_token),
        )
        assert activation.status_code == 200, activation.text
        assert activation.json()["status"] == "active"

        # The marketplace feed now exposes the advert but not its exact address.
        feed = client.get("/api/v1/properties/feed", params={"q": run_id})
        assert feed.status_code == 200, feed.text
        assert any(item["id"] == property_id for item in feed.json())

        public_property = client.get(f"/api/v1/properties/{property_id}")
        assert public_property.status_code == 200, public_property.text
        assert "physical_address" not in public_property.json()
        assert "latitude" not in public_property.json()
        assert "longitude" not in public_property.json()

        # 4. House seeker holds, books and pays for the room; Mosala confirms payment.
        hold = client.post(
            f"/api/v1/bookings/holds/{unit_id}",
            headers=_headers(seeker_token),
        )
        assert hold.status_code == 200, hold.text
        assert hold.json()["acquired"] is True

        booking = client.post(
            "/api/v1/bookings",
            headers=_headers(seeker_token),
            json={"unit_id": unit_id, "move_in_date": date.today().isoformat()},
        )
        assert booking.status_code == 201, booking.text
        booking_id = booking.json()["id"]
        assert booking.json()["status"] == "pending_payment"

        booking_payment = client.post(
            f"/api/v1/bookings/{booking_id}/payment",
            headers=_headers(seeker_token),
            json={"method": "mobile_money", "reference": f"BOOK-{run_id}"},
        )
        assert booking_payment.status_code == 200, booking_payment.text
        assert booking_payment.json()["status"] == "payment_review"

        booking_confirm = client.post(
            f"/api/v1/bookings/{booking_id}/confirm",
            headers=_headers(admin_token),
            json={"note": "Acceptance booking payment verified"},
        )
        assert booking_confirm.status_code == 200, booking_confirm.text
        assert booking_confirm.json()["status"] == "confirmed"
        assert booking_confirm.json()["payment_status"] == "confirmed"

        # Exact location is released to the confirmed seeker.
        booked_property = client.get(
            f"/api/v1/properties/{property_id}",
            headers=_headers(seeker_token),
        )
        assert booked_property.status_code == 200, booked_property.text
        assert booked_property.json()["physical_address"] == "Exact Acceptance Street, Maseru"

        # 5. Landlord checks the tenant in; booking becomes fulfilled and unit occupied.
        tenancy = client.post(
            "/api/v1/tenancies/activate",
            headers=_headers(landlord_token),
            json={"booking_id": booking_id},
        )
        assert tenancy.status_code == 201, tenancy.text
        tenancy_id = tenancy.json()["id"]
        assert tenancy.json()["status"] == "active"
        assert tenancy.json()["tenant_id"] == seeker["id"]

        my_bookings = client.get(
            "/api/v1/bookings/mine",
            headers=_headers(seeker_token),
        )
        assert my_bookings.status_code == 200, my_bookings.text
        assert next(row for row in my_bookings.json() if row["id"] == booking_id)["status"] == "fulfilled"

        units = client.get(
            f"/api/v1/properties/{property_id}/units",
            headers=_headers(landlord_token),
        )
        assert units.status_code == 200, units.text
        assert next(row for row in units.json() if row["id"] == unit_id)["status"] == "occupied"

        # 6. Tenant gives notice; the room becomes visible as a future vacancy.
        notice = client.post(
            f"/api/v1/tenancies/{tenancy_id}/notice",
            headers=_headers(seeker_token),
            json={
                "expected_move_out": (date.today() + timedelta(days=30)).isoformat(),
                "allow_readvertise": True,
                "note": "Acceptance move-out notice",
            },
        )
        assert notice.status_code == 200, notice.text
        assert notice.json()["status"] == "notice_given"

        units_after_notice = client.get(
            f"/api/v1/properties/{property_id}/units",
            headers=_headers(landlord_token),
        )
        notice_unit = next(row for row in units_after_notice.json() if row["id"] == unit_id)
        assert notice_unit["status"] == "vacating_soon"
        assert notice_unit["available_from"] == (date.today() + timedelta(days=31)).isoformat()

        future_feed = client.get("/api/v1/properties/feed", params={"q": run_id})
        assert future_feed.status_code == 200, future_feed.text
        assert any(item["id"] == property_id for item in future_feed.json())

        # 7. Move-out enters inspection; completed inspection releases the unit again.
        ended = client.post(
            f"/api/v1/tenancies/{tenancy_id}/end",
            headers=_headers(landlord_token),
        )
        assert ended.status_code == 200, ended.text
        assert ended.json()["status"] == "ended"

        inspection = client.post(
            f"/api/v1/tenancies/{tenancy_id}/inspection-complete",
            headers=_headers(landlord_token),
        )
        assert inspection.status_code == 200, inspection.text
        assert inspection.json()["inspection_completed_at"] is not None

        final_units = client.get(
            f"/api/v1/properties/{property_id}/units",
            headers=_headers(landlord_token),
        )
        assert final_units.status_code == 200, final_units.text
        final_unit = next(row for row in final_units.json() if row["id"] == unit_id)
        assert final_unit["status"] == "available"
        assert final_unit["available_from"] == date.today().isoformat()
