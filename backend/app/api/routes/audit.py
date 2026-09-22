import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.audit import AuditEvent
from app.models.rental import User, UserRole
from app.schemas.audit import AuditEventRead

router = APIRouter()


@router.get("", response_model=list[AuditEventRead])
async def list_audit_events(
    action: str | None = Query(default=None, max_length=100),
    entity_type: str | None = Query(default=None, max_length=80),
    entity_id: str | None = Query(default=None, max_length=64),
    actor_id: uuid.UUID | None = None,
    request_id: str | None = Query(default=None, max_length=64),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[AuditEvent]:
    query = select(AuditEvent)
    if action:
        query = query.where(AuditEvent.action == action.strip())
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type.strip())
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id.strip())
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    if request_id:
        query = query.where(AuditEvent.request_id == request_id.strip())
    if since:
        query = query.where(AuditEvent.created_at >= since)
    if until:
        query = query.where(AuditEvent.created_at <= until)

    rows = await db.scalars(query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit))
    return list(rows)
