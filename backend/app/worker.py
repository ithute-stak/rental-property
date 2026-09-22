import asyncio
import logging
import uuid

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.redis import get_redis
from app.services.maintenance import MaintenanceResult, run_maintenance
from app.services.realtime import publish_pending_notifications

logger = logging.getLogger("mosala.worker")
LOCK_KEY = "mosala:maintenance:lock"
_RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


async def run_cycle() -> MaintenanceResult | None:
    redis = get_redis()
    lock_token = uuid.uuid4().hex
    acquired = await redis.set(
        LOCK_KEY,
        lock_token,
        ex=settings.maintenance_lock_seconds,
        nx=True,
    )
    if not acquired:
        return None

    try:
        async with SessionFactory() as db:
            return await run_maintenance(
                db,
                viewing_reminder_hours=settings.viewing_reminder_hours,
            )
    finally:
        try:
            await redis.eval(_RELEASE_LOCK_SCRIPT, 1, LOCK_KEY, lock_token)
        except Exception:
            logger.exception("Failed to release maintenance lock")


async def run_realtime_cycle() -> int:
    redis = get_redis()
    async with SessionFactory() as db:
        published = await publish_pending_notifications(db, redis)
        await db.commit()
        return published


async def run_maintenance_forever() -> None:
    logger.info("Mosala maintenance loop started")
    while True:
        try:
            result = await run_cycle()
            if result is not None and (
                result.expired_bookings or result.viewing_reminders
            ):
                logger.info(
                    "Maintenance cycle: expired_bookings=%s viewing_reminders=%s",
                    result.expired_bookings,
                    result.viewing_reminders,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Maintenance cycle failed")
        await asyncio.sleep(settings.maintenance_interval_seconds)


async def run_realtime_forever() -> None:
    logger.info("Mosala realtime notification publisher started")
    while True:
        try:
            published = await run_realtime_cycle()
            if published:
                logger.info("Realtime notifications published=%s", published)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Realtime notification publication failed")
        await asyncio.sleep(settings.realtime_publish_interval_seconds)


async def run_forever() -> None:
    await asyncio.gather(
        run_maintenance_forever(),
        run_realtime_forever(),
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
