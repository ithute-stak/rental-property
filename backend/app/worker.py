import asyncio
import logging

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.redis import get_redis
from app.services.maintenance import MaintenanceResult, run_maintenance

logger = logging.getLogger("mosala.worker")
LOCK_KEY = "mosala:maintenance:lock"


async def run_cycle() -> MaintenanceResult | None:
    redis = get_redis()
    acquired = await redis.set(
        LOCK_KEY,
        "1",
        ex=settings.maintenance_lock_seconds,
        nx=True,
    )
    if not acquired:
        return None

    async with SessionFactory() as db:
        return await run_maintenance(
            db,
            viewing_reminder_hours=settings.viewing_reminder_hours,
        )


async def run_forever() -> None:
    logger.info("Mosala maintenance worker started")
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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
