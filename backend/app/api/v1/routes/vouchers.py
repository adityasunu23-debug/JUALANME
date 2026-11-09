"""Voucher and discount management."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.deps import AuthContext, SessionDep, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.models.voucher import Voucher, VoucherRedemption
from app.schemas.common import MessageResponse, Page
from app.schemas.marketing import (
    VoucherCreate,
    VoucherOut,
    VoucherUpdate,
    VoucherValidateRequest,
    VoucherValidateResponse,
)
from app.services import audit_service, voucher_service

router = APIRouter(prefix="/vouchers", tags=["vouchers"])

VoucherCtx = Annotated[
    AuthContext, Depends(require_permission("vouchers.manage"))
]


@router.get("", response_model=Page[VoucherOut])
async def list_vouchers(
    ctx: VoucherCtx,
    session: SessionDep,
    active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[VoucherOut]:
    conditions = []
    if active is not None:
        conditions.append(Voucher.is_active.is_(active))
    if search:
        conditions.append(Voucher.code.ilike(f"%{search.strip().upper()}%"))

    count_query = select(func.count(Voucher.id))
    query = select(Voucher)
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.order_by(Voucher.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page[VoucherOut].build(
        [VoucherOut.model_validate(row) for row in result.scalars().all()],
        total,
        page,
        page_size,
    )


@router.post("", response_model=VoucherOut, status_code=201)
async def create_voucher(
    payload: VoucherCreate, ctx: VoucherCtx, session: SessionDep
) -> VoucherOut:
    code = payload.code.strip().upper()
    existing = await session.execute(select(Voucher.id).where(Voucher.code == code))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Kode voucher sudah digunakan")
    values = payload.model_dump()
    values["code"] = code
    values["type"] = payload.type.value
    voucher = Voucher(**values)
    session.add(voucher)
    await session.flush()
    await audit_service.record(
        session, ctx.admin, "voucher.create", "voucher", voucher.id,
        f"Membuat voucher {voucher.code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return VoucherOut.model_validate(voucher)


@router.patch("/{voucher_id}", response_model=VoucherOut)
async def update_voucher(
    voucher_id: int, payload: VoucherUpdate, ctx: VoucherCtx, session: SessionDep
) -> VoucherOut:
    voucher = await session.get(Voucher, voucher_id)
    if voucher is None:
        raise NotFoundError("Voucher tidak ditemukan")
    values = payload.model_dump(exclude_unset=True)
    if "type" in values and values["type"] is not None:
        values["type"] = payload.type.value
    for key, value in values.items():
        if value is not None:
            setattr(voucher, key, value)
    await session.flush()
    await audit_service.record(
        session, ctx.admin, "voucher.update", "voucher", voucher.id,
        f"Memperbarui voucher {voucher.code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return VoucherOut.model_validate(voucher)


@router.delete("/{voucher_id}", response_model=MessageResponse)
async def delete_voucher(
    voucher_id: int, ctx: VoucherCtx, session: SessionDep
) -> MessageResponse:
    voucher = await session.get(Voucher, voucher_id)
    if voucher is None:
        raise NotFoundError("Voucher tidak ditemukan")
    code = voucher.code
    await session.delete(voucher)
    await audit_service.record(
        session, ctx.admin, "voucher.delete", "voucher", voucher_id,
        f"Menghapus voucher {code}", ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message="Voucher dihapus")


@router.get("/{voucher_id}/redemptions", response_model=list)
async def voucher_redemptions(
    voucher_id: int, ctx: VoucherCtx, session: SessionDep
) -> list:
    result = await session.execute(
        select(VoucherRedemption)
        .where(VoucherRedemption.voucher_id == voucher_id)
        .order_by(VoucherRedemption.id.desc())
        .limit(200)
    )
    return [
        {
            "id": row.id,
            "customer_id": row.customer_id,
            "order_id": row.order_id,
            "discount_amount": float(row.discount_amount),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.scalars().all()
    ]


@router.post("/validate", response_model=VoucherValidateResponse)
async def validate_voucher(
    payload: VoucherValidateRequest, ctx: VoucherCtx, session: SessionDep
) -> VoucherValidateResponse:
    try:
        voucher, discount = await voucher_service.validate_voucher(
            session, payload.code, payload.subtotal
        )
        return VoucherValidateResponse(
            valid=True,
            discount=discount,
            total=round(payload.subtotal - discount, 6),
            message=f"Voucher {voucher.code} diterapkan",
        )
    except voucher_service.VoucherError as exc:
        return VoucherValidateResponse(
            valid=False,
            discount=0,
            total=payload.subtotal,
            message=str(exc),
        )
