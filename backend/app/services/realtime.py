import json
import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Notification


def user_channel(user_id: uuid.UUID) -> str:
    return f"mosala:realtime:user:{user_id}"


def notification_event(notification: Notification) -> dict:
    created_at = notification.created_at
    return {
        "type": "notification",
        "notification": {
            "id": str(notification.id),
            "notification_type": notification.notification_type,
            "title": notification.title,
            "body": notification.body,
            "payload": notification.payload or {},
            "created_at": created_at.isoformat() if created_at else None,
        },
    }


async def publish_pending_notifications(
    db: AsyncSession,
    redis: Redis,
    *,
    limit: int = 100,
    now: datetime | None = None,
) -> int:
    rows = await db.scalars(
        select(Notification)
        .where(Notification.realtime_published_at.is_(None))
        .order_by(Notification.created_at, Notification.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    notifications = list(rows)
    published_at = now or datetime.now(timezone.utc)

    for notification in notifications:
        await redis.publish(
            user_channel(notification.user_id),
            json.dumps(notification_event(notification), separators=(",", ":")),
        )
        notification.realtime_published_at = published_at

    return len(notifications)
