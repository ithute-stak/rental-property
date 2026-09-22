from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analytics import AdminAnalyticsOverview, LandlordAnalyticsOverview


def test_analytics_routes_are_registered_and_protected():
    with TestClient(app) as client:
        admin_response = client.get("/api/v1/analytics/admin/overview")
        landlord_response = client.get("/api/v1/analytics/landlord/overview")

    assert admin_response.status_code == 401
    assert landlord_response.status_code == 401


def test_admin_analytics_money_fields_remain_decimal():
    overview = AdminAnalyticsOverview(
        active_properties=1,
        available_units=2,
        occupied_units=3,
        vacating_soon_units=1,
        active_tenancies=3,
        pending_landlord_verifications=0,
        pending_property_reviews=0,
        pending_booking_payment_reviews=0,
        pending_advert_payment_reviews=0,
        open_viewing_requests=1,
        confirmed_bookings_this_month=4,
        booking_funds_confirmed="1250.50",
        advert_revenue_confirmed="300.00",
        saved_homes=5,
        conversations=2,
        messages=9,
    )
    assert overview.booking_funds_confirmed == Decimal("1250.50")


def test_landlord_analytics_contract():
    overview = LandlordAnalyticsOverview(
        properties=2,
        active_properties=1,
        total_units=8,
        available_units=2,
        occupied_units=5,
        vacating_soon_units=1,
        active_tenancies=6,
        pending_viewings=3,
        confirmed_bookings=7,
        saved_homes=12,
        conversations=4,
        unread_messages=2,
    )
    assert overview.total_units == 8
    assert overview.unread_messages == 2
