from decimal import Decimal

from pydantic import BaseModel


class AdminAnalyticsOverview(BaseModel):
    active_properties: int
    available_units: int
    occupied_units: int
    vacating_soon_units: int
    active_tenancies: int
    pending_landlord_verifications: int
    pending_property_reviews: int
    pending_booking_payment_reviews: int
    pending_advert_payment_reviews: int
    open_viewing_requests: int
    confirmed_bookings_this_month: int
    booking_funds_confirmed: Decimal
    advert_revenue_confirmed: Decimal
    saved_homes: int
    conversations: int
    messages: int


class LandlordAnalyticsOverview(BaseModel):
    properties: int
    active_properties: int
    total_units: int
    available_units: int
    occupied_units: int
    vacating_soon_units: int
    active_tenancies: int
    pending_viewings: int
    confirmed_bookings: int
    saved_homes: int
    conversations: int
    unread_messages: int
