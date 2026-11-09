"""FastAPI dependencies: database session, current admin and permissions."""
from typing import Annotated, Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import has_permission
from app.core.security import TokenError, decode_access_token
from app.db.session import get_session
from app.models.admin import Admin

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class AuthContext:
    """Everything an endpoint needs to know about the caller."""

    def __init__(self, admin: Admin, ip: Optional[str], user_agent: Optional[str]) -> None:
        self.admin = admin
        self.ip = ip
        self.user_agent = user_agent


def client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_current_admin(
    request: Request,
    session: SessionDep,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ] = None,
) -> AuthContext:
    """Resolve the admin from a bearer token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi tidak ditemukan",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    admin_id = claims.get("sub")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Klaim token tidak valid"
        )
    result = await session.execute(select(Admin).where(Admin.id == int(admin_id)))
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun admin tidak aktif",
        )
    return AuthContext(admin, client_ip(request), request.headers.get("user-agent"))


CurrentAdmin = Annotated[AuthContext, Depends(get_current_admin)]


def require_permission(permission: str) -> Callable[..., AuthContext]:
    """Dependency factory enforcing a single permission key."""

    async def _guard(ctx: CurrentAdmin) -> AuthContext:
        if not has_permission(ctx.admin.role_enum, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {ctx.admin.role} tidak memiliki izin {permission}",
            )
        return ctx

    return _guard


def require_owner() -> Callable[..., AuthContext]:
    async def _guard(ctx: CurrentAdmin) -> AuthContext:
        if ctx.admin.role_enum.value != "OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya Owner yang dapat mengakses sumber daya ini",
            )
        return ctx

    return _guard


async def get_idempotency_key(
    idempotency_key: Annotated[Optional[str], Header(alias="Idempotency-Key")] = None
) -> Optional[str]:
    return idempotency_key