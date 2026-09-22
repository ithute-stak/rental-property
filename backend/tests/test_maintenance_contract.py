from app.models.booking import PaymentStatus
from app.models.rental import UnitStatus
from app.models.tenancy import Tenancy
from app.services.maintenance import MaintenanceResult, unit_status_after_booking_release


def test_expired_payment_status_is_stable():
    assert PaymentStatus.EXPIRED.value == "expired"


def test_booking_release_returns_normal_unit_to_available():
    assert unit_status_after_booking_release(None) == UnitStatus.AVAILABLE.value


def test_booking_release_preserves_future_vacancy_state():
    notice = Tenancy(allow_readvertise=True)
    assert unit_status_after_booking_release(notice) == UnitStatus.VACATING_SOON.value


def test_booking_release_preserves_nonadvertised_notice_state():
    notice = Tenancy(allow_readvertise=False)
    assert unit_status_after_booking_release(notice) == UnitStatus.NOTICE_GIVEN.value


def test_maintenance_result_defaults_to_zero_counts():
    assert MaintenanceResult().expired_bookings == 0
    assert MaintenanceResult().viewing_reminders == 0
