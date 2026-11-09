"""Inventory operations with atomic locking to prevent double delivery."""
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Product
from app.models.stock import StockItem

MAX_IMPORT_LINES = 50000


class OutOfStockError(Exception):
    """Raised when a product cannot satisfy the requested quantity."""

    def __init__(self, product_id: int, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Stok tidak cukup untuk produk {product_id}: diminta {requested}, tersedia {available}"
        )


def parse_lines(raw_text: str) -> List[str]:
    """Split text into non-empty, trimmed deliverable lines."""
    if not raw_text:
        return []
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n")]
    return [line for line in lines if line]


def parse_csv(raw_text: str) -> List[str]:
    """Read the first column of a CSV payload as deliverable content."""
    reader = csv.reader(io.StringIO(raw_text.replace("\r\n", "\n")))
    rows: List[str] = []
    for row in reader:
        if not row:
            continue
        cell = (row[0] or "").strip()
        if not cell:
            continue
        if cell.lower() in ("content", "stock", "stok", "item", "code", "key"):
            continue
        rows.append(cell)
    return rows


async def count_available(session: AsyncSession, product_id: int) -> int:
    result = await session.execute(
        select(func.count(StockItem.id)).where(
            StockItem.product_id == product_id, StockItem.is_used.is_(False)
        )
    )
    return int(result.scalar() or 0)


async def count_sold(session: AsyncSession, product_id: int) -> int:
    result = await session.execute(
        select(func.count(StockItem.id)).where(
            StockItem.product_id == product_id, StockItem.is_used.is_(True)
        )
    )
    return int(result.scalar() or 0)


async def available_map(session: AsyncSession, product_ids: Sequence[int]) -> dict:
    if not product_ids:
        return {}
    result = await session.execute(
        select(StockItem.product_id, func.count(StockItem.id))
        .where(StockItem.product_id.in_(list(product_ids)), StockItem.is_used.is_(False))
        .group_by(StockItem.product_id)
    )
    return {row[0]: int(row[1]) for row in result.all()}


async def sold_map(session: AsyncSession, product_ids: Sequence[int]) -> dict:
    if not product_ids:
        return {}
    result = await session.execute(
        select(StockItem.product_id, func.count(StockItem.id))
        .where(StockItem.product_id.in_(list(product_ids)), StockItem.is_used.is_(True))
        .group_by(StockItem.product_id)
    )
    return {row[0]: int(row[1]) for row in result.all()}


async def add_stock(
    session: AsyncSession,
    product_id: int,
    lines: Iterable[str],
    source: str = "manual",
    label: Optional[str] = None,
    deduplicate: bool = True,
    batch_id: Optional[str] = None,
) -> Tuple[int, int]:
    """Insert stock rows. Returns (imported, duplicates_skipped)."""
    cleaned = [line.strip() for line in lines if line and line.strip()]
    if not cleaned:
        return 0, 0
    if len(cleaned) > MAX_IMPORT_LINES:
        raise ValueError(f"Maksimal {MAX_IMPORT_LINES} baris per impor")

    existing: set = set()
    if deduplicate:
        result = await session.execute(
            select(StockItem.content).where(StockItem.product_id == product_id)
        )
        existing = {row[0] for row in result.all()}

    batch = batch_id or uuid.uuid4().hex[:12]
    imported = 0
    duplicates = 0
    for line in cleaned:
        if deduplicate and line in existing:
            duplicates += 1
            continue
        session.add(
            StockItem(
                product_id=product_id,
                content=line,
                label=label,
                source=source,
                batch_id=batch,
            )
        )
        if deduplicate:
            existing.add(line)
        imported += 1
    await session.flush()
    return imported, duplicates


async def reserve_stock(
    session: AsyncSession, product_id: int, quantity: int, order_id: int
) -> List[StockItem]:
    """Atomically claim `quantity` unused items for an order.

    Each row is claimed with a conditional UPDATE (is_used = false) so two
    concurrent deliveries can never receive the same item.
    """
    if quantity <= 0:
        raise ValueError("Quantity harus lebih dari 0")

    now = datetime.now(timezone.utc)
    candidate_result = await session.execute(
        select(StockItem.id)
        .where(StockItem.product_id == product_id, StockItem.is_used.is_(False))
        .order_by(StockItem.id.asc())
        .limit(quantity * 5)
    )
    candidate_ids = [row[0] for row in candidate_result.all()]

    claimed: List[int] = []
    for stock_id in candidate_ids:
        if len(claimed) >= quantity:
            break
        result = await session.execute(
            update(StockItem)
            .where(StockItem.id == stock_id, StockItem.is_used.is_(False))
            .values(
                is_used=True,
                order_id=order_id,
                reserved_at=now,
                used_at=now,
            )
        )
        if result.rowcount == 1:
            claimed.append(stock_id)

    if len(claimed) < quantity:
        await release_stock(session, order_id, commit=False)
        available = await count_available(session, product_id)
        raise OutOfStockError(product_id, quantity, available)

    rows = await session.execute(select(StockItem).where(StockItem.id.in_(claimed)))
    return list(rows.scalars().all())


async def release_stock(
    session: AsyncSession, order_id: int, commit: bool = False
) -> int:
    """Return reserved items of an order back to the pool."""
    result = await session.execute(
        update(StockItem)
        .where(StockItem.order_id == order_id, StockItem.is_used.is_(True))
        .values(is_used=False, order_id=None, reserved_at=None, used_at=None)
    )
    if commit:
        await session.commit()
    return int(result.rowcount or 0)


async def delete_stock_items(session: AsyncSession, ids: Sequence[int]) -> int:
    if not ids:
        return 0
    result = await session.execute(
        delete(StockItem).where(StockItem.id.in_(list(ids)), StockItem.is_used.is_(False))
    )
    return int(result.rowcount or 0)