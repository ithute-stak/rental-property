from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.engagement import ViewingStatus
from app.schemas.engagement import ViewingDecision, ViewingRequestCreate


def test_viewing_status_values_are_stable():
    assert ViewingStatus.PENDING.value == "pending"
    assert ViewingStatus.ACCEPTED.value == "accepted"
    assert ViewingStatus.RESCHEDULED.value == "rescheduled"


def test_viewing_request_requires_future_time():
    with pytest.raises(ValidationError):
        ViewingRequestCreate(
            property_id="00000000-0000-0000-0000-000000000001",
            preferred_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )


def test_accepting_viewing_requires_scheduled_time():
    with pytest.raises(ValidationError):
        ViewingDecision(status="accepted")
