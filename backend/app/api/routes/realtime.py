import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import SessionFactory
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.models.rental import User
from app.services.realtime import user_channel

router = APIRouter()


async def _authenticate(websocket: WebSocket) -> User | None:
    try:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        if message.get("type") != "authenticate" or not isinstance(message.get("token"), str):
            return None
        user_id, _ = decode_access_token(message["token"])
    except (asyncio.TimeoutError, ValueError, WebSocketDisconnect, json.JSONDecodeError, TypeError):
        return None

    async with SessionFactory() as db:
        return await db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))


@router.websocket("/events")
async def realtime_events(websocket: WebSocket) -> None:
    await websocket.accept()
    user = await _authenticate(websocket)
    if user is None:
        await websocket.close(code=4401, reason="Authentication required")
        return

    redis = get_redis()
    pubsub = redis.pubsub()
    channel = user_channel(user.id)
    await pubsub.subscribe(channel)
    await websocket.send_json({"type": "ready"})

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20.0)
            if message is None:
                await websocket.send_json(
                    {
                        "type": "ping",
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                continue

            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            if isinstance(data, str):
                await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
