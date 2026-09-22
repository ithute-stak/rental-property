import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.models.booking import Notification
from app.services.realtime import notification_event, realtime_channel


def test_realtime_channel_is_scoped_to_user_uuid():
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert realtime_channel(user_id) == (
        "mosala:realtime:user:11111111-1111-1111-1111-111111111111"
    )


def test_notification_event_preserves_notification_identity_and_payload():
    notification = Notification(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        notification_type="booking_confirmed",
        title="Your room is booked",
        body="Booking confirmed.",
        payload={"booking_id": "booking-1"},
        created_at=datetime(2026, 9, 22, 13, 0, tzinfo=timezone.utc),
    )

    event = notification_event(notification)

    assert event["type"] == "notification.created"
    assert event["notification"]["id"] == "22222222-2222-2222-2222-222222222222"
    assert event["notification"]["notification_type"] == "booking_confirmed"
    assert event["notification"]["payload"] == {"booking_id": "booking-1"}
    assert event["notification"]["created_at"] == "2026-09-22T13:00:00+00:00"


def test_realtime_websocket_rejects_invalid_token_without_query_string_auth():
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/realtime") as websocket:
            websocket.send_json({"type": "authenticate", "token": "not-a-valid-jwt"})
            with pytest.raises(WebSocketDisconnect) as exc_info:
                websocket.receive_json()

    assert exc_info.value.code == 4401
