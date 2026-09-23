import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.database import SessionFactory, engine
from app.main import app
from app.models.payment import PaymentProviderEvent
from app.provision_admin import provision_admin

ADMIN_PASSWORD = "MosalaReconciliationAdmin123!"
USER_PASSWORD = "MosalaReconciliationUser123!"


def _phone() -> str:
    return f"+266{uuid.uuid4().int % 100_000_000:08d}"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap_case(admin_phone: str, event_id: uuid.UUID, source_id: uuid.UUID) -> None:
    async with SessionFactory() as db:
        await provision_admin(
            db,
            phone=admin_phone,
            display_name="Payment Reconciliation Admin",
            password=ADMIN_PASSWORD,
        )
        db.add(
            PaymentProviderEvent(
                id=event_id,
                provider="fakepay",
                event_id=f"evt-{uuid.uuid4().hex}",
                event_type="payment.refunded",
                provider_transaction_id=f"tx-{uuid.uuid4().hex}",
                source_type="booking",
                source_id=source_id,
                outcome="refunded",
                amount=Decimal("1000.00"),
                currency="LSL",
                occurred_at=datetime.now(timezone.utc),
                payload_sha256="a" * 64,
                processing_status="manual_review",
                processing_message="Provider reported a refund; reconciliation is required",
                processed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    await engine.dispose()


def test_admin_can_reconcile_provider_event_with_audit_trail() -> None:
    admin_phone = _phone()
    event_id = uuid.uuid4()
    source_id = uuid.uuid4()
    asyncio.run(_bootstrap_case(admin_phone, event_id, source_id))

    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": admin_phone, "password": ADMIN_PASSWORD},
        )
        assert admin_login.status_code == 200, admin_login.text
        admin_session = admin_login.json()
        admin_token = admin_session["access_token"]
        admin_id = admin_session["user"]["id"]

        registered = client.post(
            "/api/v1/auth/register",
            json={
                "phone": _phone(),
                "display_name": "Reconciliation Non Admin",
                "password": USER_PASSWORD,
                "role": "house_seeker",
            },
        )
        assert registered.status_code == 201, registered.text
        non_admin_phone = registered.json()["phone"]
        non_admin_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": non_admin_phone, "password": USER_PASSWORD},
        )
        assert non_admin_login.status_code == 200, non_admin_login.text
        non_admin_token = non_admin_login.json()["access_token"]

        forbidden = client.get(
            "/api/v1/admin/payment-reconciliation/events",
            headers=_auth(non_admin_token),
        )
        assert forbidden.status_code == 403

        queue = client.get(
            "/api/v1/admin/payment-reconciliation/events",
            headers=_auth(admin_token),
        )
        assert queue.status_code == 200, queue.text
        event = next(item for item in queue.json() if item["id"] == str(event_id))
        assert event["processing_status"] == "manual_review"
        assert event["processing_message"] == "Provider reported a refund; reconciliation is required"
        assert event["resolution_note"] is None
        assert event["reconciled_at"] is None
        assert "payload_sha256" not in event

        detail = client.get(
            f"/api/v1/admin/payment-reconciliation/events/{event_id}",
            headers=_auth(admin_token),
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["source_id"] == str(source_id)

        note = "Refund matched the bank settlement report and the booking ledger was reconciled."
        resolved = client.post(
            f"/api/v1/admin/payment-reconciliation/events/{event_id}/resolve",
            headers=_auth(admin_token),
            json={"note": note},
        )
        assert resolved.status_code == 200, resolved.text
        resolved_event = resolved.json()
        assert resolved_event["processing_status"] == "resolved"
        assert resolved_event["resolution_note"] == note
        assert resolved_event["reconciled_by"] == admin_id
        assert resolved_event["reconciled_at"] is not None
        assert (
            resolved_event["processing_message"]
            == "Provider reported a refund; reconciliation is required"
        )

        duplicate_resolution = client.post(
            f"/api/v1/admin/payment-reconciliation/events/{event_id}/resolve",
            headers=_auth(admin_token),
            json={"note": "Second resolution should be rejected"},
        )
        assert duplicate_resolution.status_code == 409

        open_queue = client.get(
            "/api/v1/admin/payment-reconciliation/events",
            headers=_auth(admin_token),
        )
        assert open_queue.status_code == 200, open_queue.text
        assert all(item["id"] != str(event_id) for item in open_queue.json())

        resolved_queue = client.get(
            "/api/v1/admin/payment-reconciliation/events",
            headers=_auth(admin_token),
            params={"processing_status": "resolved", "provider": "FAKEPAY"},
        )
        assert resolved_queue.status_code == 200, resolved_queue.text
        assert any(item["id"] == str(event_id) for item in resolved_queue.json())

        audit = client.get(
            "/api/v1/admin/audit",
            headers=_auth(admin_token),
            params={
                "action": "payment_provider.reconciliation_resolved",
                "entity_type": "payment_provider_event",
                "entity_id": str(event_id),
            },
        )
        assert audit.status_code == 200, audit.text
        events = audit.json()
        assert len(events) == 1
        audit_event = events[0]
        assert audit_event["actor_id"] == admin_id
        assert audit_event["details"]["provider"] == "fakepay"
        assert audit_event["details"]["source_id"] == str(source_id)
        assert audit_event["details"]["from_status"] == "manual_review"
        assert audit_event["details"]["to_status"] == "resolved"
        assert audit_event["details"]["resolution_note"] == note
