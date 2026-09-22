import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionFactory, engine
from app.main import app
from app.provision_admin import provision_admin


def _phone() -> str:
    return f"+266{uuid.uuid4().int % 100_000_000:08d}"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap_admin(phone: str, password: str) -> str:
    async with SessionFactory() as db:
        user = await provision_admin(
            db,
            phone=phone,
            display_name="Mosala Acceptance Admin",
            password=password,
        )
        user_id = str(user.id)
    # The acceptance test then runs the application under TestClient's event
    # loop. Empty the async engine pool so asyncpg connections are not reused
    # across event loops.
    await engine.dispose()
    return user_id


def _register_and_login(
    client: TestClient,
    *,
    role: str,
    display_name: str,
    password: str,
) -> tuple[dict, str]:
    phone = _phone()
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "display_name": display_name,
            "password": password,
            "role": role,
        },
    )
    assert registered.status_code == 201, registered.text

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": phone, "password": password},
    )
    assert login.status_code == 200, login.text
    session = login.json()
    return session["user"], session["access_token"]


def _feed_ids(client: TestClient) -> set[str]:
    response = client.get("/api/v1/properties/feed")
    assert response.status_code == 200, response.text
    return {str(item["id"]) for item in response.json()}


@pytest.mark.acceptance
def test_complete_mosala_rental_lifecycle() -> None:
    suffix = uuid.uuid4().hex[:10]
    admin_phone = _phone()
    admin_password = "MosalaAcceptanceAdmin123!"
    asyncio.run(_bootstrap_admin(admin_phone, admin_password))

    landlord_password = "MosalaLandlord123!"
    seeker_password = "MosalaSeeker123!"

    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": admin_phone, "password": admin_password},
        )
        assert admin_login.status_code == 200, admin_login.text
        admin_token = admin_login.json()["access_token"]

        landlord, landlord_token = _register_and_login(
            client,
            role="landlord",
            display_name=f"Acceptance Landlord {suffix}",
            password=landlord_password,
        )
        seeker, seeker_token = _register_and_login(
            client,
            role="house_seeker",
            display_name=f"Acceptance Seeker {suffix}",
            password=seeker_password,
        )

        # 1. Mosala verifies the landlord.
        profile = client.put(
            "/api/v1/landlords/me",
            headers=_auth(landlord_token),
            json={
                "business_name": f"Acceptance Rentals {suffix}",
                "physical_address": "Kingsway, Maseru",
            },
        )
        assert profile.status_code == 200, profile.text

        submitted_profile = client.post(
            "/api/v1/landlords/me/submit",
            headers=_auth(landlord_token),
        )
        assert submitted_profile.status_code == 200, submitted_profile.text
        assert submitted_profile.json()["verification_status"] == "pending"

        verified_profile = client.patch(
            f"/api/v1/admin/landlords/{landlord['id']}/verification",
            headers=_auth(admin_token),
            json={"approved": True},
        )
        assert verified_profile.status_code == 200, verified_profile.text
        assert verified_profile.json()["verification_status"] == "approved"

        # 2. Landlord creates a property and its rentable unit.
        property_title = f"Acceptance Home {suffix}"
        property_response = client.post(
            "/api/v1/properties",
            headers=_auth(landlord_token),
            json={
                "title": property_title,
                "description": "End-to-end Mosala acceptance property",
                "property_type": "rooms",
                "physical_address": "12 Acceptance Street, Maseru",
                "district": "Maseru",
                "town": "Maseru",
                "area": "Thetsane",
                "latitude": -29.3300,
                "longitude": 27.4500,
                "total_rooms": 1,
                "security_level": "gated",
                "security_features": {
                    "wall": True,
                    "gate": True,
                    "outdoor_lighting": True,
                },
            },
        )
        assert property_response.status_code == 201, property_response.text
        property_row = property_response.json()
        property_id = str(property_row["id"])
        assert property_row["status"] == "draft"

        unit_response = client.post(
            f"/api/v1/properties/{property_id}/units",
            headers=_auth(landlord_token),
            json={
                "name": "Room 1",
                "monthly_rent": "2500.00",
                "deposit": "1000.00",
                "available_from": date.today().isoformat(),
            },
        )
        assert unit_response.status_code == 201, unit_response.text
        unit = unit_response.json()
        unit_id = str(unit["id"])
        assert unit["status"] == "available"

        submitted_property = client.post(
            f"/api/v1/properties/{property_id}/submit",
            headers=_auth(landlord_token),
        )
        assert submitted_property.status_code == 200, submitted_property.text
        assert submitted_property.json()["status"] == "pending_verification"

        # 3. Mosala approves the advert, charges it, verifies payment and activates it.
        approved = client.post(
            f"/api/v1/admin/properties/{property_id}/approve",
            headers=_auth(admin_token),
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"

        quoted = client.put(
            f"/api/v1/admin/properties/{property_id}/charge",
            headers=_auth(admin_token),
            json={"amount": "150.00", "waive": False, "note": "Acceptance advert charge"},
        )
        assert quoted.status_code == 200, quoted.text
        assert quoted.json()["status"] == "quoted"

        advert_reference = f"ADV-{suffix}"
        advert_payment = client.post(
            f"/api/v1/advertising/properties/{property_id}/charge/payment",
            headers=_auth(landlord_token),
            json={"method": "mobile_money", "reference": advert_reference},
        )
        assert advert_payment.status_code == 200, advert_payment.text
        assert advert_payment.json()["status"] == "payment_submitted"

        confirmed_advert_payment = client.post(
            f"/api/v1/admin/properties/{property_id}/charge/confirm",
            headers=_auth(admin_token),
            json={"note": "Acceptance payment verified"},
        )
        assert confirmed_advert_payment.status_code == 200, confirmed_advert_payment.text
        assert confirmed_advert_payment.json()["status"] == "paid"

        activated = client.post(
            f"/api/v1/admin/properties/{property_id}/activate",
            headers=_auth(admin_token),
        )
        assert activated.status_code == 200, activated.text
        assert activated.json()["status"] == "active"
        assert property_id in _feed_ids(client)

        # Exact address/GPS is hidden until the seeker has an accepted viewing
        # or confirmed booking.
        public_property = client.get(f"/api/v1/properties/{property_id}")
        assert public_property.status_code == 200, public_property.text
        assert "physical_address" not in public_property.json()
        assert "latitude" not in public_property.json()
        assert "longitude" not in public_property.json()

        # 4. Seeker saves the home, requests a viewing and the landlord accepts it.
        saved = client.post(
            f"/api/v1/engagement/favourites/{property_id}",
            headers=_auth(seeker_token),
        )
        assert saved.status_code == 201, saved.text

        viewing_time = datetime.now(timezone.utc) + timedelta(days=2)
        viewing = client.post(
            "/api/v1/engagement/viewings",
            headers=_auth(seeker_token),
            json={
                "property_id": property_id,
                "preferred_at": viewing_time.isoformat(),
                "message": "I would like to inspect the room.",
            },
        )
        assert viewing.status_code == 201, viewing.text
        viewing_id = str(viewing.json()["id"])
        assert viewing.json()["status"] == "pending"

        accepted_viewing = client.post(
            f"/api/v1/engagement/viewings/{viewing_id}/decision",
            headers=_auth(landlord_token),
            json={
                "status": "accepted",
                "scheduled_at": viewing_time.isoformat(),
                "note": "Viewing confirmed",
            },
        )
        assert accepted_viewing.status_code == 200, accepted_viewing.text
        assert accepted_viewing.json()["status"] == "accepted"

        exact_property = client.get(
            f"/api/v1/properties/{property_id}",
            headers=_auth(seeker_token),
        )
        assert exact_property.status_code == 200, exact_property.text
        assert exact_property.json()["physical_address"] == "12 Acceptance Street, Maseru"
        assert "latitude" in exact_property.json()
        assert "longitude" in exact_property.json()

        # 5. Seeker holds and books the room, submits payment, and Mosala confirms it.
        hold = client.post(
            f"/api/v1/bookings/holds/{unit_id}",
            headers=_auth(seeker_token),
        )
        assert hold.status_code == 200, hold.text
        assert hold.json()["acquired"] is True

        booking = client.post(
            "/api/v1/bookings",
            headers=_auth(seeker_token),
            json={"unit_id": unit_id, "move_in_date": date.today().isoformat()},
        )
        assert booking.status_code == 201, booking.text
        booking_id = str(booking.json()["id"])
        assert booking.json()["status"] == "pending_payment"
        assert property_id not in _feed_ids(client)

        booking_reference = f"BOOK-{suffix}"
        submitted_booking_payment = client.post(
            f"/api/v1/bookings/{booking_id}/payment",
            headers=_auth(seeker_token),
            json={"method": "mobile_money", "reference": booking_reference},
        )
        assert submitted_booking_payment.status_code == 200, submitted_booking_payment.text
        assert submitted_booking_payment.json()["status"] == "payment_review"
        assert submitted_booking_payment.json()["payment_status"] == "submitted"

        confirmed_booking = client.post(
            f"/api/v1/bookings/{booking_id}/confirm",
            headers=_auth(admin_token),
            json={"note": "Acceptance booking payment verified"},
        )
        assert confirmed_booking.status_code == 200, confirmed_booking.text
        assert confirmed_booking.json()["status"] == "confirmed"
        assert confirmed_booking.json()["payment_status"] == "confirmed"

        # 6. Landlord checks the tenant in. The seeker account becomes a tenant.
        tenancy_response = client.post(
            "/api/v1/tenancies/activate",
            headers=_auth(landlord_token),
            json={"booking_id": booking_id},
        )
        assert tenancy_response.status_code == 201, tenancy_response.text
        tenancy = tenancy_response.json()
        tenancy_id = str(tenancy["id"])
        assert tenancy["status"] == "active"

        me_after_checkin = client.get(
            "/api/v1/auth/me",
            headers=_auth(seeker_token),
        )
        assert me_after_checkin.status_code == 200, me_after_checkin.text
        assert me_after_checkin.json()["id"] == seeker["id"]
        assert me_after_checkin.json()["role"] == "tenant"

        bookings_after_checkin = client.get(
            "/api/v1/bookings/mine",
            headers=_auth(seeker_token),
        )
        assert bookings_after_checkin.status_code == 200, bookings_after_checkin.text
        matching_booking = next(
            item for item in bookings_after_checkin.json() if str(item["id"]) == booking_id
        )
        assert matching_booking["status"] == "fulfilled"

        # 7. Tenant gives notice. The room is advertised again for a future occupant.
        move_out = date.today() + timedelta(days=30)
        notice = client.post(
            f"/api/v1/tenancies/{tenancy_id}/notice",
            headers=_auth(seeker_token),
            json={
                "expected_move_out": move_out.isoformat(),
                "allow_readvertise": True,
                "note": "Acceptance move-out notice",
            },
        )
        assert notice.status_code == 200, notice.text
        assert notice.json()["status"] == "notice_given"
        assert notice.json()["expected_move_out"] == move_out.isoformat()
        assert property_id in _feed_ids(client)

        units_during_notice = client.get(f"/api/v1/properties/{property_id}/units")
        assert units_during_notice.status_code == 200, units_during_notice.text
        notice_unit = next(item for item in units_during_notice.json() if str(item["id"]) == unit_id)
        assert notice_unit["status"] == "vacating_soon"
        assert notice_unit["available_from"] == (move_out + timedelta(days=1)).isoformat()

        # 8. Landlord records move-out and inspection. The unit returns to AVAILABLE.
        ended = client.post(
            f"/api/v1/tenancies/{tenancy_id}/end",
            headers=_auth(landlord_token),
        )
        assert ended.status_code == 200, ended.text
        assert ended.json()["status"] == "ended"
        assert property_id not in _feed_ids(client)

        inspected = client.post(
            f"/api/v1/tenancies/{tenancy_id}/inspection-complete",
            headers=_auth(landlord_token),
        )
        assert inspected.status_code == 200, inspected.text
        assert inspected.json()["inspection_completed_at"] is not None

        final_units = client.get(f"/api/v1/properties/{property_id}/units")
        assert final_units.status_code == 200, final_units.text
        final_unit = next(item for item in final_units.json() if str(item["id"]) == unit_id)
        assert final_unit["status"] == "available"
        assert final_unit["available_from"] == date.today().isoformat()
        assert property_id in _feed_ids(client)
