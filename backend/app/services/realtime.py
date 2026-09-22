import json
import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Notification


def realtime_channel(user_id: uuid.UUID) -> str:
    return f"mosala:realtime:user:{user_id}"


def notification_event(notification: Notification) -> dict:
    return {
        "type": "notification.created",
        "notification": {
            "id": str(notification.id),
            "notification_type": notification.notification_type,
            "title": notification.title,
            "body": notification.body,
            "payload": notification.payload or {},
            "read_at": (
                notification.read_at.isoformat() if notification.read_at is not None else None
            ),
            "created_at": notification.created_at.isoformat(),
        },
    }


async def relay_pending_notifications(
    db: AsyncSession,
    redis: Redis,
    *,
    batch_size: int = 100,
    now: datetime | None = None,
) -> int:
    published_at = now or datetime.now(timezone.utc)
    rows = await db.scalars(
        select(Notification)
        .where(Notification.realtime_published_at.is_(None))
        .order_by(Notification.created_at, Notification.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    notifications = list(rows)

    for notification in notifications:
        event = notification_event(notification)
        await redis.publish(
            realtime_channel(notification.user_id),
            json.dumps(event, separators=(",", ":"), ensure_ascii=False),
        )
        notification.realtime_published_at = published_at

    if notifications:
        await db.commit()
    return len(notifications)
