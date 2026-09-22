from fastapi import APIRouter

from app.api.routes import bookings, health, properties

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
