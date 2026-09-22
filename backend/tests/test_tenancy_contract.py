from datetime import date, timedelta

from app.models.rental import UnitStatus
from app.models.tenancy import TenancyStatus
from app.schemas.tenancy import TenantNoticeCreate


def test_notice_defaults_to_readvertise():
    notice = TenantNoticeCreate(expected_move_out=date.today() + timedelta(days=30))
    assert notice.allow_readvertise is True


def test_notice_and_unit_lifecycle_values_are_stable():
    assert TenancyStatus.ACTIVE.value == "active"
    assert TenancyStatus.NOTICE_GIVEN.value == "notice_given"
    assert UnitStatus.VACATING_SOON.value == "vacating_soon"
    assert UnitStatus.INSPECTION.value == "inspection"
