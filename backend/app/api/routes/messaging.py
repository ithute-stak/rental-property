import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.models.booking import Notification
from app.models.messaging import Conversation, Message
from app.models.rental import Property, PropertyStatus, User, UserRole
from app.schemas.messaging import ConversationCreate, ConversationRead, MessageCreate, MessageRead

router = APIRouter()


def _notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str,
    **payload: str,
) -> None:
    db.add(
        Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            payload=payload,
        )
    )


async def _conversation_or_404(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user: User,
) -> Conversation:
    row = await db.get(Conversation, conversation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if user.id not in {row.seeker_id, row.landlord_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation access denied")
    return row


async def _conversation_read(
    db: AsyncSession,
    row: Conversation,
    user: User,
) -> ConversationRead:
    property_row = await db.get(Property, row.property_id)
    other_id = row.landlord_id if user.id == row.seeker_id else row.seeker_id
    other = await db.get(User, other_id)
    if property_row is None or other is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation records are incomplete",
        )
    last = await db.scalar(
        select(Message)
        .where(Message.conversation_id == row.id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    unread_count = await db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == row.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
    )
    return ConversationRead(
        id=row.id,
        property_id=row.property_id,
        property_title=property_row.title,
        other_party_id=other.id,
        other_party_name=other.display_name,
        last_message=last.body if last else None,
        last_message_at=last.created_at if last else None,
        unread_count=int(unread_count or 0),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _message_read(
    db: AsyncSession,
    row: Message,
    user: User,
) -> MessageRead:
    sender = await db.get(User, row.sender_id)
    if sender is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Message sender is missing")
    return MessageRead(
        id=row.id,
        conversation_id=row.conversation_id,
        sender_id=row.sender_id,
        sender_name=sender.display_name,
        body=row.body,
        created_at=row.created_at,
        read_at=row.read_at,
        is_mine=row.sender_id == user.id,
    )


@router.post(
    "/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_conversation(
    payload: ConversationCreate,
    user: User = Depends(require_roles(UserRole.HOUSE_SEEKER.value, UserRole.TENANT.value)),
    db: AsyncSession = Depends(get_db),
) -> ConversationRead:
    property_row = await db.get(Property, payload.property_id)
    if property_row is None or property_row.status != PropertyStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active property not found")
    if property_row.owner_id == user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You own this property")

    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.property_id == property_row.id,
            Conversation.seeker_id == user.id,
            Conversation.landlord_id == property_row.owner_id,
        )
    )
    if conversation is None:
        conversation = Conversation(
            property_id=property_row.id,
            seeker_id=user.id,
            landlord_id=property_row.owner_id,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    return await _conversation_read(db, conversation, user)


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationRead]:
    rows = await db.scalars(
        select(Conversation)
        .where(or_(Conversation.seeker_id == user.id, Conversation.landlord_id == user.id))
        .order_by(Conversation.updated_at.desc())
    )
    return [await _conversation_read(db, row, user) for row in rows]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    await _conversation_or_404(db, conversation_id, user)
    rows = list(
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
    )
    rows.reverse()
    return [await _message_read(db, row, user) for row in rows]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    conversation = await _conversation_or_404(db, conversation_id, user)
    recipient_id = (
        conversation.landlord_id if user.id == conversation.seeker_id else conversation.seeker_id
    )
    message = Message(
        conversation_id=conversation.id,
        sender_id=user.id,
        body=payload.body,
    )
    db.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    _notify(
        db,
        recipient_id,
        "message_received",
        f"New message from {user.display_name}",
        payload.body[:180],
        conversation_id=str(conversation.id),
        property_id=str(conversation.property_id),
    )
    await db.commit()
    await db.refresh(message)
    return await _message_read(db, message, user)


@router.post("/conversations/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_conversation_read(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _conversation_or_404(db, conversation_id, user)
    await db.execute(
        update(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
