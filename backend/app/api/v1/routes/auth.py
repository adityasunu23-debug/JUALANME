"""Admin authentication endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentAdmin, SessionDep, client_ip
from app.core.rbac import permissions_for_role
from app.core.security import create_access_token, verify_telegram_login
from app.models.admin import Admin
from app.models.enums import AdminRole
from app.schemas.auth import (
    AdminProfile,
    DevLoginRequest,
    TelegramLoginRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse


router = APIRouter(prefix="/auth", tags=["auth"])


def _profile(admin: Admin) -> AdminProfile:
    return AdminProfile(
        id=admin.id,
        telegram_id=admin.telegram_id,
        username=admin.username,
        first_name=admin.first_name,
        last_name=admin.last_name,
        photo_url=admin.photo_url,
        role=admin.role,
        is_active=admin.is_active,
        permissions=sorted(permissions_for_role(admin.role_enum)),
    )


def _token(admin: Admin) -> TokenResponse:
    token = create_access_token(
        subject=str(admin.id), extra_claims={"role": admin.role}
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        admin=_profile(admin),
    )


async def _find_admin(session, telegram_id: int):
    result = await session.execute(
        select(Admin).where(Admin.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(
    payload: DevLoginRequest, request: Request, session: SessionDep
) -> TokenResponse:
    """Development-only login without the Telegram widget."""
    if not settings.dev_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login dinonaktifkan",
        )
    admin = await _find_admin(session, payload.telegram_id)
    if admin is None:
        admin = Admin(
            telegram_id=payload.telegram_id,
            username=f"dev_{payload.telegram_id}",
            first_name="Developer",
            role=AdminRole.OWNER.value,
            is_active=True,
        )
        session.add(admin)
        await session.flush()
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Akun admin tidak aktif")

    admin.last_login_at = datetime.now(timezone.utc)
    admin.last_login_ip = client_ip(request)
    await session.commit()
    return _token(admin)


@router.post("/telegram-login", response_model=TokenResponse)
async def telegram_login(
    payload: TelegramLoginRequest, request: Request, session: SessionDep
) -> TokenResponse:
    """Authenticate with the Telegram Login Widget."""
    data = payload.model_dump()
    if not verify_telegram_login(data, settings.bot_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Data Telegram Login tidak valid atau kedaluwarsa",
        )

    admin = await _find_admin(session, payload.id)
    if admin is None and payload.id in settings.admin_telegram_id_list:
        admin = Admin(
            telegram_id=payload.id,
            role=AdminRole.SUPER_ADMIN.value,
            is_active=True,
        )
        session.add(admin)
        await session.flush()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda belum terdaftar sebagai admin",
        )
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Akun admin tidak aktif")

    admin.username = payload.username
    admin.first_name = payload.first_name
    admin.last_name = payload.last_name
    admin.photo_url = payload.photo_url
    admin.last_login_at = datetime.now(timezone.utc)
    admin.last_login_ip = client_ip(request)
    await session.commit()
    return _token(admin)


@router.get("/me", response_model=AdminProfile)
async def me(ctx: CurrentAdmin) -> AdminProfile:
    return _profile(ctx.admin)


@router.post("/logout", response_model=MessageResponse)
async def logout() -> MessageResponse:
    return MessageResponse(message="Berhasil keluar")
