import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.models.rental import User
from app.services.realtime import realtime_channel

router = APIRouter()

_UNAUTHORIZED = 4401
_BAD_PROTOCOL = 4400


async def _authenticated_user(auth_message: object) -> User | None:
    if not isinstance(auth_message, dict) or auth_message.get("type") != "authenticate":
        return None
    token = auth_message.get("token")
    if not isinstance(token, str) or not token.strip():
        return None
    try:
        user_id, _ = decode_access_token(token.strip())
    except ValueError:
        return None

    async with SessionFactory() as db:
        return await db.scalar(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )


@router.websocket("/realtime")
async def realtime_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        auth_message = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=settings.websocket_auth_timeout_seconds,
        )
    except WebSocketDisconnect:
        return
    except (asyncio.TimeoutError, ValueError, TypeError):
        await websocket.close(code=_BAD_PROTOCOL, reason="Authentication message required")
        return

    user = await _authenticated_user(auth_message)
    if user is None:
        await websocket.close(code=_UNAUTHORIZED, reason="Authentication failed")
        return

    channel_name = realtime_channel(user.id)
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(channel_name)
    await websocket.send_json(
        {
            "type": "ready",
            "user_id": str(user.id),
            "heartbeat_seconds": settings.websocket_heartbeat_seconds,
        }
    )

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=settings.websocket_heartbeat_seconds,
            )
            if message is not None and message.get("type") == "message":
                payload = message.get("data")
                if isinstance(payload, str):
                    await websocket.send_text(payload)
                else:
                    await websocket.send_json(payload)
            else:
                await websocket.send_json(
                    {
                        "type": "ping",
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                )
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        try:
            await pubsub.unsubscribe(channel_name)
        finally:
            await pubsub.aclose()
