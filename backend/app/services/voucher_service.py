"""Voucher validation and redemption."""
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VoucherType
from app.models.voucher import Voucher, VoucherRedemption


class VoucherError(Exception):
    """Raised when a voucher cannot be applied."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def compute_discount(voucher: Voucher, subtotal: float) -> float:
    """Return the discount amount for a given subtotal."""
    if subtotal <= 0:
        return 0.0
    if voucher.type == VoucherType.PERCENT.value:
        discount = subtotal * (float(voucher.value) / 100.0)
    else:
        discount = float(voucher.value)
    if voucher.max_discount is not None:
        discount = min(discount, float(voucher.max_discount))
    return round(min(discount, subtotal), 6)


async def find_voucher(session: AsyncSession, code: str) -> Optional[Voucher]:
    normalized = (code or "").strip().upper()
    if not normalized:
        return None
    result = await session.execute(select(Voucher).where(Voucher.code == normalized))
    return result.scalar_one_or_none()


async def validate_voucher(
    session: AsyncSession,
    code: str,
    subtotal: float,
    customer_id: Optional[int] = None,
) -> Tuple[Voucher, float]:
    """Validate a code and return (voucher, discount). Raises VoucherError."""
    voucher = await find_voucher(session, code)
    if voucher is None:
        raise VoucherError("Kode voucher tidak ditemukan")
    if not voucher.is_active:
        raise VoucherError("Voucher tidak aktif")

    now = _now()
    valid_from = _as_aware(voucher.valid_from)
    valid_until = _as_aware(voucher.valid_until)
    if valid_from and now < valid_from:
        raise VoucherError("Voucher belum berlaku")
    if valid_until and now > valid_until:
        raise VoucherError("Voucher sudah kedaluwarsa")
    if voucher.usage_limit and voucher.used_count >= voucher.usage_limit:
        raise VoucherError("Kuota voucher sudah habis")
    if subtotal < float(voucher.min_purchase or 0):
        raise VoucherError(
            f"Minimal pembelian {float(voucher.min_purchase):.2f} untuk voucher ini"
        )

    if customer_id and voucher.per_customer_limit:
        used_result = await session.execute(
            select(func.count(VoucherRedemption.id)).where(
                VoucherRedemption.voucher_id == voucher.id,
                VoucherRedemption.customer_id == customer_id,
            )
        )
        if int(used_result.scalar() or 0) >= voucher.per_customer_limit:
            raise VoucherError("Voucher sudah Anda gunakan")

    discount = compute_discount(voucher, subtotal)
    if discount <= 0:
        raise VoucherError("Voucher tidak menghasilkan diskon")
    return voucher, discount


async def redeem_voucher(
    session: AsyncSession,
    voucher: Voucher,
    customer_id: int,
    order_id: Optional[int],
    discount: float,
) -> None:
    """Record a redemption and bump the usage counter."""
    session.add(
        VoucherRedemption(
            voucher_id=voucher.id,
            customer_id=customer_id,
            order_id=order_id,
            discount_amount=discount,
        )
    )
    voucher.used_count = int(voucher.used_count or 0) + 1
    await session.flush()


async def release_redemption(session: AsyncSession, order_id: int) -> None:
    """Undo a redemption when an order is cancelled or expires."""
    result = await session.execute(
        select(VoucherRedemption).where(VoucherRedemption.order_id == order_id)
    )
    redemption = result.scalar_one_or_none()
    if redemption is None:
        return
    voucher_result = await session.execute(
        select(Voucher).where(Voucher.id == redemption.voucher_id)
    )
    voucher = voucher_result.scalar_one_or_none()
    if voucher is not None:
        voucher.used_count = max(0, int(voucher.used_count or 0) - 1)
    await session.delete(redemption)
    await session.flush()