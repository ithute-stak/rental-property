from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import consume_rate_limit, rate_limit_key
from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password, verify_password
from app.models.rental import LandlordProfile, User, UserRole
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenRead,
    UserRead,
)
from app.services.sessions import (
    InvalidRefreshToken,
    RefreshTokenReuseDetected,
    issue_refresh_token,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter()
_DUMMY_PASSWORD_HASH = hash_password("mosala-invalid-account-password")


def _token_response(user: User, refresh_token: str) -> TokenRead:
    return TokenRead(
        access_token=create_access_token(user.id, user.role),
        refresh_token=refresh_token,
        expires_in_seconds=settings.access_token_minutes * 60,
        refresh_expires_in_seconds=settings.refresh_token_days * 24 * 60 * 60,
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    phone = payload.phone.strip()
    email = payload.email.strip().lower() if payload.email else None

    duplicate_filters = [User.phone == phone]
    if email:
        duplicate_filters.append(func.lower(User.email) == email)

    existing = await db.scalar(select(User).where(or_(*duplicate_filters)))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone or email already exists",
        )

    user = User(
        email=email,
        phone=phone,
        display_name=payload.display_name.strip(),
        role=payload.role,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()

    if payload.role == UserRole.LANDLORD.value:
        db.add(LandlordProfile(user_id=user.id))

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenRead)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenRead:
    identifier = payload.identifier.strip()
    limit_key = rate_limit_key("login", identifier)
    allowed, retry_after = await consume_rate_limit(
        redis,
        key=limit_key,
        limit=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    query = select(User).where(
        or_(
            User.phone == identifier,
            func.lower(User.email) == identifier.lower(),
        )
    )
    user = await db.scalar(query)
    password_hash = user.hashed_password if user is not None else _DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)
    if user is None or not user.is_active or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        )

    await redis.delete(limit_key)
    refresh = await issue_refresh_token(db, user_id=user.id)
    await db.commit()
    return _token_response(user, refresh.raw_token)


@router.post("/refresh", response_model=TokenRead)
async def refresh_session(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenRead:
    try:
        user, refresh = await rotate_refresh_token(db, payload.refresh_token)
    except RefreshTokenReuseDetected as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session reuse detected. Please sign in again.",
        ) from exc
    except InvalidRefreshToken as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session is invalid or expired",
        ) from exc
    return _token_response(user, refresh.raw_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    await revoke_refresh_token(db, payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await revoke_all_user_refresh_tokens(db, user.id)


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
