import asyncio
import logging
import uuid

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.redis import get_redis
from app.services.maintenance import MaintenanceResult, run_maintenance
from app.services.realtime import relay_pending_notifications

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
    async with SessionFactory() as db:
        return await relay_pending_notifications(
            db,
            get_redis(),
            batch_size=settings.notification_relay_batch_size,
        )


async def run_forever() -> None:
    logger.info("Mosala maintenance and realtime worker started")
    loop = asyncio.get_running_loop()
    next_maintenance_at = 0.0

    while True:
        try:
            relayed = await run_realtime_cycle()
            if relayed:
                logger.info("Realtime relay: notifications=%s", relayed)

            now = loop.time()
            if now >= next_maintenance_at:
                result = await run_cycle()
                next_maintenance_at = now + settings.maintenance_interval_seconds
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
            logger.exception("Worker cycle failed")

        await asyncio.sleep(settings.notification_relay_interval_seconds)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
