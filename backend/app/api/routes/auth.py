from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.rental import LandlordProfile, User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenRead, UserRead

router = APIRouter()


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
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenRead:
    identifier = payload.identifier.strip()
    query = select(User).where(
        or_(
            User.phone == identifier,
            func.lower(User.email) == identifier.lower(),
        )
    )
    user = await db.scalar(query)
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        )

    token = create_access_token(user.id, user.role)
    return TokenRead(
        access_token=token,
        expires_in_seconds=settings.access_token_minutes * 60,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
