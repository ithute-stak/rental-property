import uuid
from datetime import datetime, timezone

from app.models.booking import Notification
from app.services.realtime import notification_event, user_channel


def test_user_channel_is_scoped_to_one_user():
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert user_channel(user_id) == "mosala:realtime:user:11111111-1111-1111-1111-111111111111"


def test_notification_event_is_deduplicatable_and_preserves_payload():
    notification = Notification(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        notification_type="booking_confirmed",
        title="Your room is booked",
        body="Booking confirmed.",
        payload={"booking_id": "abc"},
        created_at=datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc),
    )

    event = notification_event(notification)

    assert event["type"] == "notification"
    assert event["notification"]["id"] == "22222222-2222-2222-2222-222222222222"
    assert event["notification"]["notification_type"] == "booking_confirmed"
    assert event["notification"]["payload"] == {"booking_id": "abc"}
    assert event["notification"]["created_at"] == "2026-09-22T12:00:00+00:00"
