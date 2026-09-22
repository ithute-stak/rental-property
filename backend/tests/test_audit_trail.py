import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from app.core.database import SessionFactory
from app.core.request_context import current_request_id
from app.main import app
from app.models.audit import AuditEvent
from app.services.audit import add_audit_event


def test_admin_audit_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/audit")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_audit_events_redact_sensitive_details_and_are_append_only() -> None:
    entity_id = uuid.uuid4()
    request_token = current_request_id.set("audit-test-request")
    try:
        async with SessionFactory() as db:
            event = add_audit_event(
                db,
                action="test.audit_created",
                entity_type="test_entity",
                entity_id=entity_id,
                details={
                    "status": "created",
                    "payment_reference": "SHOULD-NOT-BE-STORED",
                    "nested": {"refresh_token": "SHOULD-NOT-BE-STORED"},
                },
            )
            await db.commit()
            await db.refresh(event)
            event_id = event.id

            assert event.request_id == "audit-test-request"
            assert event.entity_id == str(entity_id)
            assert event.details["status"] == "created"
            assert event.details["payment_reference"] == "[redacted]"
            assert event.details["nested"]["refresh_token"] == "[redacted]"

            event.action = "test.audit_mutated"
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()

            persisted = await db.get(AuditEvent, event_id)
            assert persisted is not None
            assert persisted.action == "test.audit_created"
    finally:
        current_request_id.reset(request_token)
