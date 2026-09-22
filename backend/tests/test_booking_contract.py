import pytest
from pydantic import ValidationError

from app.models.booking import BookingStatus, PaymentStatus
from app.schemas.booking import BookingPaymentSubmit


def test_booking_lifecycle_statuses_are_stable():
    assert BookingStatus.PENDING_PAYMENT.value == "pending_payment"
    assert BookingStatus.PAYMENT_REVIEW.value == "payment_review"
    assert BookingStatus.CONFIRMED.value == "confirmed"
    assert BookingStatus.FULFILLED.value == "fulfilled"
    assert PaymentStatus.CONFIRMED.value == "confirmed"


def test_booking_payment_method_is_restricted():
    payment = BookingPaymentSubmit(method="mobile_money", reference="MP-123")
    assert payment.method == "mobile_money"

    with pytest.raises(ValidationError):
        BookingPaymentSubmit(method="crypto", reference="x")
