"""Admin accounts, roles and audit logs."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.deps import AuthContext, SessionDep, require_owner, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.core.rbac import ALL_PERMISSIONS, PERMISSIONS, permissions_for_role
from app.models.admin import Admin
from app.models.audit import AuditLog
from app.models.enums import AdminRole
from app.schemas.admin import (
    AdminCreate,
    AdminOut,
    AdminUpdate,
    AuditLogOut,
    RoleOption,
)
from app.schemas.common import Page
from app.services import audit_service

router = APIRouter(tags=["admins"])

OwnerCtx = Annotated[AuthContext, Depends(require_owner())]
LogsCtx = Annotated[AuthContext, Depends(require_permission("logs.view"))]


@router.get("/admins/roles", response_model=List[RoleOption])
async def list_roles(ctx: OwnerCtx) -> List[RoleOption]:
    return [
        RoleOption(
            value=role.value,
            label=role.label,
            permissions=sorted(permissions_for_role(role)),
        )
        for role in AdminRole
    ]


@router.get("/admins", response_model=Page[AdminOut])
async def list_admins(
    ctx: OwnerCtx,
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[AdminOut]:
    total = int((await session.execute(select(func.count(Admin.id)))).scalar() or 0)
    result = await session.execute(
        select(Admin)
        .order_by(Admin.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page[AdminOut].build(
        [AdminOut.model_validate(row) for row in result.scalars().all()],
        total,
        page,
        page_size,
    )


@router.post("/admins", response_model=AdminOut, status_code=201)
async def create_admin(
    payload: AdminCreate, ctx: OwnerCtx, session: SessionDep
) -> AdminOut:
    existing = await session.execute(
        select(Admin).where(Admin.telegram_id == payload.telegram_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Telegram ID ini sudah terdaftar sebagai admin")
    admin = Admin(
        telegram_id=payload.telegram_id,
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role.value,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    session.add(admin)
    await session.flush()
    await audit_service.record(
        session,
        ctx.admin,
        "admin.create",
        "admin",
        admin.id,
        f"Membuat admin {admin.display_name} ({admin.role})",
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return AdminOut.model_validate(admin)


@router.patch("/admins/{admin_id}", response_model=AdminOut)
async def update_admin(
    admin_id: int, payload: AdminUpdate, ctx: OwnerCtx, session: SessionDep
) -> AdminOut:
    admin = await session.get(Admin, admin_id)
    if admin is None:
        raise NotFoundError("Admin tidak ditemukan")
    values = payload.model_dump(exclude_unset=True)
    if admin.id == ctx.admin.id and values.get("is_active") is False:
        raise ConflictError("Tidak dapat menonaktifkan akun sendiri")
    if "role" in values and values["role"] is not None:
        role = values["role"]
        values["role"] = role.value if isinstance(role, AdminRole) else str(role)
    for key, value in values.items():
        if value is not None:
            setattr(admin, key, value)
    await session.flush()
    await audit_service.record(
        session,
        ctx.admin,
        "admin.update",
        "admin",
        admin.id,
        f"Memperbarui admin {admin.display_name}",
        details=values,
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return AdminOut.model_validate(admin)


@router.delete("/admins/{admin_id}", response_model=AdminOut)
async def deactivate_admin(
    admin_id: int, ctx: OwnerCtx, session: SessionDep
) -> AdminOut:
    admin = await session.get(Admin, admin_id)
    if admin is None:
        raise NotFoundError("Admin tidak ditemukan")
    if admin.id == ctx.admin.id:
        raise ConflictError("Tidak dapat menonaktifkan akun sendiri")
    admin.is_active = False
    await session.flush()
    await audit_service.record(
        session,
        ctx.admin,
        "admin.deactivate",
        "admin",
        admin.id,
        f"Menonaktifkan admin {admin.display_name}",
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return AdminOut.model_validate(admin)


@router.get("/permissions", response_model=List[str])
async def list_permissions(ctx: OwnerCtx) -> List[str]:
    return list(ALL_PERMISSIONS)


@router.get("/logs", response_model=Page[AuditLogOut])
async def list_logs(
    ctx: LogsCtx,
    session: SessionDep,
    action: Optional[str] = None,
    admin_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
) -> Page[AuditLogOut]:
    conditions = []
    if action:
        conditions.append(AuditLog.action.ilike(f"%{action}%"))
    if admin_id:
        conditions.append(AuditLog.admin_id == admin_id)

    count_query = select(func.count(AuditLog.id))
    query = select(AuditLog).order_by(AuditLog.id.desc())
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    return Page[AuditLogOut].build(
        [AuditLogOut.model_validate(row) for row in result.scalars().all()],
        total,
        page,
        page_size,
    )
