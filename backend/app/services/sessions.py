import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_refresh_token, hash_refresh_token
from app.models.auth import RefreshToken
from app.models.rental import User


class InvalidRefreshToken(ValueError):
    pass


class RefreshTokenReuseDetected(InvalidRefreshToken):
    pass


@dataclass(frozen=True)
class IssuedRefreshToken:
    raw_token: str
    row: RefreshToken


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def issue_refresh_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> IssuedRefreshToken:
    current = now or utcnow()
    raw_token = create_refresh_token()
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id or uuid.uuid4(),
        expires_at=current + timedelta(days=settings.refresh_token_days),
    )
    db.add(row)
    await db.flush()
    return IssuedRefreshToken(raw_token=raw_token, row=row)


async def rotate_refresh_token(
    db: AsyncSession,
    raw_token: str,
    *,
    now: datetime | None = None,
) -> tuple[User, IssuedRefreshToken]:
    current = now or utcnow()
    token_hash = hash_refresh_token(raw_token)
    row = await db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    if row is None:
        raise InvalidRefreshToken("Refresh token is invalid")

    if row.revoked_at is not None:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == row.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=current)
        )
        await db.commit()
        raise RefreshTokenReuseDetected("Refresh token reuse detected; session revoked")

    if row.expires_at <= current:
        row.revoked_at = current
        await db.commit()
        raise InvalidRefreshToken("Refresh token has expired")

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        row.revoked_at = current
        await db.commit()
        raise InvalidRefreshToken("Refresh session is no longer active")

    replacement = await issue_refresh_token(
        db,
        user_id=user.id,
        family_id=row.family_id,
        now=current,
    )
    row.revoked_at = current
    row.last_used_at = current
    row.replaced_by_id = replacement.row.id
    await db.commit()
    return user, replacement


async def revoke_refresh_token(
    db: AsyncSession,
    raw_token: str,
    *,
    now: datetime | None = None,
) -> None:
    current = now or utcnow()
    row = await db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if row is not None and row.revoked_at is None:
        row.revoked_at = current
        await db.commit()


async def revoke_all_user_refresh_tokens(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> int:
    current = now or utcnow()
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=current)
    )
    await db.commit()
    return int(result.rowcount or 0)
