from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.advertising import AdvertChargeStatus
from app.schemas.advertising import AdvertChargePaymentSubmit, AdvertChargeQuote


def test_advert_charge_statuses_are_stable():
    assert AdvertChargeStatus.QUOTED.value == "quoted"
    assert AdvertChargeStatus.PAYMENT_SUBMITTED.value == "payment_submitted"
    assert AdvertChargeStatus.PAID.value == "paid"
    assert AdvertChargeStatus.WAIVED.value == "waived"


def test_advert_charge_quote_rejects_negative_amount():
    with pytest.raises(ValidationError):
        AdvertChargeQuote(amount=Decimal("-1"))


def test_advert_payment_method_is_restricted():
    payment = AdvertChargePaymentSubmit(method="mobile_money", reference="AD-100")
    assert payment.method == "mobile_money"

    with pytest.raises(ValidationError):
        AdvertChargePaymentSubmit(method="crypto", reference="AD-100")
