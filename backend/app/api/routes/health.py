from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.database import SessionFactory
from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    try:
        async with SessionFactory() as db:
            await db.execute(text("SELECT 1"))
        redis_ok = await get_redis().ping()
        if not redis_ok:
            raise RuntimeError("Redis ping failed")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependencies are not ready",
        ) from exc

    return {"status": "ready", "database": "ok", "redis": "ok"}
