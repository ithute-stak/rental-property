import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement

from app.core.database import SessionFactory, engine
from app.core.security import hash_password
from app.main import app
from app.models.booking import Booking, BookingPayment, BookingStatus, PaymentStatus
from app.models.rental import Property, PropertyStatus, Unit, UnitStatus, User, UserRole
from app.services.payment_providers import (
    NormalizedPaymentEvent,
    PaymentWebhookPayloadError,
    PaymentWebhookSignatureError,
    register_payment_provider,
    unregister_payment_provider,
)

PASSWORD = "ProviderWebhookTest123!"
SECRET = b"mosala-provider-test-secret"
PROVIDER = "fakepay"


class FakeHmacAdapter:
    async def verify_and_parse(self, *, body: bytes, headers) -> NormalizedPaymentEvent:
        supplied = headers.get("x-test-signature", "")
        expected = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise PaymentWebhookSignatureError("signature mismatch")
        try:
            payload = json.loads(body)
            occurred_at = payload.get("occurred_at")
            return NormalizedPaymentEvent(
                event_id=str(payload["event_id"]),
                event_type=str(payload["event_type"]),
                provider_transaction_id=payload.get("transaction_id"),
                source_type=str(payload["source_type"]),
                source_id=uuid.UUID(str(payload["source_id"])),
                outcome=str(payload["outcome"]),
                amount=Decimal(str(payload["amount"])) if payload.get("amount") is not None else None,
                currency=payload.get("currency"),
                occurred_at=(datetime.fromisoformat(occurred_at) if occurred_at else None),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PaymentWebhookPayloadError("invalid test provider payload") from exc


def _signed_body(payload: dict) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return body, {"content-type": "application/json", "x-test-signature": signature}


def _phone() -> str:
    return f"+266{uuid.uuid4().int % 100_000_000:08d}"


async def _seed_pending_booking() -> tuple[uuid.UUID, str]:
    owner_id = uuid.uuid4()
    seeker_id = uuid.uuid4()
    property_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    seeker_phone = _phone()

    async with SessionFactory() as db:
        db.add_all(
            [
                User(
                    id=owner_id,
                    phone=_phone(),
                    display_name="Provider Test Landlord",
                    role=UserRole.LANDLORD.value,
                    hashed_password=hash_password(PASSWORD),
                    is_active=True,
                ),
                User(
                    id=seeker_id,
                    phone=seeker_phone,
                    display_name="Provider Test Seeker",
                    role=UserRole.HOUSE_SEEKER.value,
                    hashed_password=hash_password(PASSWORD),
                    is_active=True,
                ),
            ]
        )
        await db.flush()

        db.add(
            Property(
                id=property_id,
                owner_id=owner_id,
                title="Provider Test Home",
                description="Webhook payment test property",
                property_type="house",
                status=PropertyStatus.ACTIVE.value,
                physical_address="Provider Test Street, Maseru",
                district="Maseru",
                town="Maseru",
                area="Central",
                latitude=Decimal("-29.315100"),
                longitude=Decimal("27.486900"),
                location=WKTElement("POINT(27.4869 -29.3151)", srid=4326),
                total_rooms=1,
                security_level="standard",
                security_features={},
            )
        )
        await db.flush()

        db.add(
            Unit(
                id=unit_id,
                property_id=property_id,
                name="Room 1",
                monthly_rent=Decimal("2500.00"),
                deposit=Decimal("1000.00"),
                status=UnitStatus.BOOKING_PENDING.value,
                available_from=date.today(),
            )
        )
        await db.flush()

        db.add(
            Booking(
                id=booking_id,
                unit_id=unit_id,
                seeker_id=seeker_id,
                status=BookingStatus.PENDING_PAYMENT.value,
                move_in_date=date.today() + timedelta(days=2),
                amount_due=Decimal("1000.00"),
                currency="LSL",
                payment_due_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        await db.flush()

        db.add(
            BookingPayment(
                booking_id=booking_id,
                amount=Decimal("1000.00"),
                currency="LSL",
                status=PaymentStatus.PENDING.value,
            )
        )
        await db.commit()
    await engine.dispose()
    return booking_id, seeker_phone


def test_unknown_payment_provider_is_not_exposed() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/payments/webhooks/not-configured", content=b"{}")
    assert response.status_code == 404


def test_signed_provider_payment_is_idempotent_and_enters_mosala_review() -> None:
    booking_id, seeker_phone = asyncio.run(_seed_pending_booking())
    register_payment_provider(PROVIDER, FakeHmacAdapter())
    event = {
        "event_id": f"evt-{uuid.uuid4().hex}",
        "event_type": "payment.completed",
        "transaction_id": f"provider-tx-{uuid.uuid4().hex}",
        "source_type": "booking",
        "source_id": str(booking_id),
        "outcome": "paid",
        "amount": "1000.00",
        "currency": "LSL",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    body, headers = _signed_body(event)

    try:
        with TestClient(app) as client:
            bad_signature = client.post(
                f"/api/v1/payments/webhooks/{PROVIDER}",
                content=body,
                headers={**headers, "x-test-signature": "invalid"},
            )
            assert bad_signature.status_code == 401

            received = client.post(
                f"/api/v1/payments/webhooks/{PROVIDER}",
                content=body,
                headers=headers,
            )
            assert received.status_code == 200, received.text
            receipt = received.json()
            assert receipt["duplicate"] is False
            assert receipt["processing_status"] == "processed"

            login = client.post(
                "/api/v1/auth/login",
                json={"identifier": seeker_phone, "password": PASSWORD},
            )
            assert login.status_code == 200, login.text
            token = login.json()["access_token"]
            bookings = client.get(
                "/api/v1/bookings/mine",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert bookings.status_code == 200, bookings.text
            row = next(item for item in bookings.json() if item["id"] == str(booking_id))
            assert row["status"] == BookingStatus.PAYMENT_REVIEW.value
            assert row["payment_status"] == PaymentStatus.SUBMITTED.value
            assert row["payment_method"] == f"provider:{PROVIDER}"
            assert row["payment_reference"] == event["transaction_id"].upper()

            replay = client.post(
                f"/api/v1/payments/webhooks/{PROVIDER}",
                content=body,
                headers=headers,
            )
            assert replay.status_code == 200, replay.text
            assert replay.json()["duplicate"] is True
            assert replay.json()["provider_event_id"] == receipt["provider_event_id"]

            mutated = {**event, "amount": "1001.00"}
            mutated_body, mutated_headers = _signed_body(mutated)
            conflict = client.post(
                f"/api/v1/payments/webhooks/{PROVIDER}",
                content=mutated_body,
                headers=mutated_headers,
            )
            assert conflict.status_code == 409
    finally:
        unregister_payment_provider(PROVIDER)
