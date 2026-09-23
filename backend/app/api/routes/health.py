import asyncio

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.redis import get_redis
from app.core.storage import storage

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "release": settings.release_sha,
    }


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    try:
        async with SessionFactory() as db:
            await db.execute(text("SELECT 1"))
        redis_ok = await get_redis().ping()
        if not redis_ok:
            raise RuntimeError("Redis ping failed")
        await asyncio.wait_for(asyncio.to_thread(storage.check_ready), timeout=3.0)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependencies are not ready",
        ) from exc

    return {
        "status": "ready",
        "database": "ok",
        "redis": "ok",
        "object_storage": "ok",
    }
