import argparse
import asyncio
import getpass
import os

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionFactory
from app.core.security import hash_password
from app.models.rental import User, UserRole


def validate_admin_inputs(
    phone: str | None,
    display_name: str,
    password: str,
) -> tuple[str | None, str]:
    normalized_phone = phone.strip() if phone and phone.strip() else None
    normalized_name = display_name.strip()
    if normalized_phone is not None and len(normalized_phone) < 7:
        raise ValueError("Admin phone must contain at least 7 characters when supplied")
    if len(normalized_name) < 2:
        raise ValueError("Admin display name must contain at least 2 characters")
    if len(password) < 8:
        raise ValueError("Admin password must contain at least 8 characters")
    return normalized_phone, normalized_name


async def provision_admin(
    db: AsyncSession,
    *,
    phone: str | None,
    display_name: str,
    password: str,
    email: str | None = None,
    update_existing: bool = False,
) -> User:
    normalized_phone, normalized_name = validate_admin_inputs(phone, display_name, password)
    normalized_email = email.strip().lower() if email and email.strip() else None
    if normalized_phone is None and normalized_email is None:
        raise ValueError("Admin provisioning requires an email address or phone number")

    filters = []
    if normalized_phone is not None:
        filters.append(User.phone == normalized_phone)
    if normalized_email is not None:
        filters.append(func.lower(User.email) == normalized_email)
    matches = list(await db.scalars(select(User).where(or_(*filters))))

    unique_matches = {row.id: row for row in matches}
    if len(unique_matches) > 1:
        raise ValueError("Phone and email belong to different existing accounts")

    existing = next(iter(unique_matches.values()), None)
    if existing is not None and not update_existing:
        raise ValueError(
            "An account with this phone or email already exists; use --update-existing deliberately"
        )

    if existing is None:
        user = User(
            phone=normalized_phone,
            email=normalized_email,
            display_name=normalized_name,
            role=UserRole.ADMIN.value,
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add(user)
    else:
        user = existing
        if normalized_phone is not None:
            user.phone = normalized_phone
        if normalized_email is not None:
            user.email = normalized_email
        user.display_name = normalized_name
        user.role = UserRole.ADMIN.value
        user.hashed_password = hash_password(password)
        user.is_active = True

    await db.commit()
    await db.refresh(user)
    return user


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create the initial Mosala administrator or deliberately update an existing account."
    )
    parser.add_argument("--phone", default=os.getenv("MOSALA_ADMIN_PHONE"))
    parser.add_argument("--name", default=os.getenv("MOSALA_ADMIN_NAME"))
    parser.add_argument("--email", default=os.getenv("MOSALA_ADMIN_EMAIL"))
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Promote/reset an existing matching account instead of refusing the operation.",
    )
    return parser


async def _run(args: argparse.Namespace, password: str) -> User:
    async with SessionFactory() as db:
        return await provision_admin(
            db,
            phone=args.phone,
            display_name=args.name,
            email=args.email,
            password=password,
            update_existing=args.update_existing,
        )


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if not args.email and not args.phone:
        parser.error("--email/MOSALA_ADMIN_EMAIL or --phone/MOSALA_ADMIN_PHONE is required")
    if not args.name:
        parser.error("--name or MOSALA_ADMIN_NAME is required")

    password = os.getenv("MOSALA_ADMIN_PASSWORD")
    if password is None:
        password = getpass.getpass("Mosala admin password: ")

    try:
        user = asyncio.run(_run(args, password))
    except ValueError as exc:
        parser.error(str(exc))

    identifier = user.email or user.phone or str(user.id)
    print(f"Mosala administrator ready: {identifier} ({user.id})")


if __name__ == "__main__":
    main()
