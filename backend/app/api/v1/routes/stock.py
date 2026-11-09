"""Stock inventory management, import and export."""
import csv
import io
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.deps import AuthContext, SessionDep, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.models.catalog import Product
from app.models.stock import StockItem
from app.schemas.common import BulkDeleteRequest, MessageResponse, Page
from app.schemas.stock import (
    StockBulkCreate,
    StockImportResult,
    StockItemOut,
    StockSummary,
    StockUpdate,
)
from app.services import audit_service, catalog_service, settings_service, stock_service

router = APIRouter(prefix="/stock", tags=["stock"])

StockCtx = Annotated[AuthContext, Depends(require_permission("stock.manage"))]


@router.get("/summary", response_model=List[StockSummary])
async def stock_summary(ctx: StockCtx, session: SessionDep) -> List[StockSummary]:
    threshold = await settings_service.get_int(
        session, "delivery.stock_low_threshold", default=5
    )
    rows = await catalog_service.stock_summaries(session)
    return [
        StockSummary(
            **row,
            low_stock=row["available"] <= threshold,
        )
        for row in rows
    ]


@router.get("", response_model=Page[StockItemOut])
async def list_stock(
    ctx: StockCtx,
    session: SessionDep,
    product_id: Optional[int] = None,
    used: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=500),
) -> Page[StockItemOut]:
    conditions = []
    if product_id:
        conditions.append(StockItem.product_id == product_id)
    if used is not None:
        conditions.append(StockItem.is_used.is_(used))
    if search:
        conditions.append(StockItem.content.ilike(f"%{search.strip()}%"))

    count_query = select(func.count(StockItem.id))
    query = select(StockItem).order_by(StockItem.id.desc())
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    return Page[StockItemOut].build(
        [StockItemOut.model_validate(row) for row in result.scalars().all()],
        total,
        page,
        page_size,
    )


@router.post("", response_model=StockImportResult)
async def add_stock(
    payload: StockBulkCreate, ctx: StockCtx, session: SessionDep
) -> StockImportResult:
    product = await session.get(Product, payload.product_id)
    if product is None:
        raise NotFoundError("Produk tidak ditemukan")
    imported, duplicates = await stock_service.add_stock(
        session,
        payload.product_id,
        payload.lines,
        source="manual",
        label=payload.label,
        deduplicate=payload.deduplicate,
    )
    await audit_service.record(
        session, ctx.admin, "stock.add", "product", payload.product_id,
        f"Menambah {imported} stok untuk {product.name_id}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return StockImportResult(
        imported=imported,
        skipped=duplicates,
        duplicates=duplicates,
        message=f"{imported} stok ditambahkan, {duplicates} duplikat dilewati",
    )


@router.post("/import", response_model=StockImportResult)
async def import_stock_file(
    ctx: StockCtx,
    session: SessionDep,
    product_id: int = Form(...),
    deduplicate: bool = Form(True),
    label: Optional[str] = Form(None),
    file: UploadFile = File(...),
) -> StockImportResult:
    product = await session.get(Product, product_id)
    if product is None:
        raise NotFoundError("Produk tidak ditemukan")
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        lines = stock_service.parse_csv(raw)
    else:
        lines = stock_service.parse_lines(raw)
    if not lines:
        raise ConflictError("Berkas tidak berisi stok yang valid")

    imported, duplicates = await stock_service.add_stock(
        session,
        product_id,
        lines,
        source="import",
        label=label,
        deduplicate=deduplicate,
    )
    await audit_service.record(
        session, ctx.admin, "stock.import", "product", product_id,
        f"Impor {imported} stok dari {file.filename}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return StockImportResult(
        imported=imported,
        skipped=duplicates,
        duplicates=duplicates,
        message=f"{imported} stok diimpor dari {file.filename}",
    )


@router.get("/export")
async def export_stock(
    ctx: StockCtx,
    session: SessionDep,
    product_id: Optional[int] = None,
    used: Optional[bool] = None,
) -> StreamingResponse:
    query = select(StockItem).order_by(StockItem.id.asc())
    if product_id:
        query = query.where(StockItem.product_id == product_id)
    if used is not None:
        query = query.where(StockItem.is_used.is_(used))
    result = await session.execute(query)
    rows = list(result.scalars().all())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "product_id", "content", "label", "is_used", "order_id", "created_at"])
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.product_id,
                row.content,
                row.label or "",
                "1" if row.is_used else "0",
                row.order_id or "",
                row.created_at.isoformat() if row.created_at else "",
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="stock-export.csv"'
        },
    )


@router.patch("/{stock_id}", response_model=StockItemOut)
async def update_stock(
    stock_id: int, payload: StockUpdate, ctx: StockCtx, session: SessionDep
) -> StockItemOut:
    item = await session.get(StockItem, stock_id)
    if item is None:
        raise NotFoundError("Item stok tidak ditemukan")
    if item.is_used:
        raise ConflictError("Stok yang sudah terjual tidak dapat diubah")
    if payload.content is not None:
        item.content = payload.content
    if payload.label is not None:
        item.label = payload.label
    await session.flush()
    await audit_service.record(
        session, ctx.admin, "stock.update", "stock", stock_id,
        "Memperbarui item stok", ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return StockItemOut.model_validate(item)


@router.delete("/{stock_id}", response_model=MessageResponse)
async def delete_stock(
    stock_id: int, ctx: StockCtx, session: SessionDep
) -> MessageResponse:
    item = await session.get(StockItem, stock_id)
    if item is None:
        raise NotFoundError("Item stok tidak ditemukan")
    if item.is_used:
        raise ConflictError("Stok yang sudah terjual tidak dapat dihapus")
    await session.delete(item)
    await audit_service.record(
        session, ctx.admin, "stock.delete", "stock", stock_id,
        "Menghapus item stok", ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message="Item stok dihapus")


@router.post("/bulk-delete", response_model=MessageResponse)
async def bulk_delete_stock(
    payload: BulkDeleteRequest, ctx: StockCtx, session: SessionDep
) -> MessageResponse:
    deleted = await stock_service.delete_stock_items(session, payload.ids)
    await audit_service.record(
        session, ctx.admin, "stock.bulk_delete", "stock", None,
        f"Menghapus {deleted} item stok", details=payload.ids, ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message=f"{deleted} item stok dihapus")
