from fastapi import APIRouter

from app.api.routes import admin, auth, bookings, health, landlords, media, notifications, properties, tenancies

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(landlords.router, prefix="/landlords", tags=["landlords"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(media.router, prefix="/properties", tags=["property-media"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(tenancies.router, prefix="/tenancies", tags=["tenancies"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
