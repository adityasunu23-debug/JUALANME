"""Category and product management endpoints."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.deps import AuthContext, SessionDep, require_permission
from app.core.exceptions import NotFoundError
from app.models.catalog import Category, Product
from app.schemas.catalog import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from app.schemas.common import BulkDeleteRequest, MessageResponse, Page
from app.services import audit_service, catalog_service

router = APIRouter(tags=["catalog"])

CategoryCtx = Annotated[AuthContext, Depends(require_permission("categories.manage"))]
ProductCtx = Annotated[AuthContext, Depends(require_permission("products.manage"))]


@router.get("/categories", response_model=List[CategoryOut])
async def list_categories(
    ctx: CategoryCtx,
    session: SessionDep,
    active_only: bool = False,
    search: Optional[str] = None,
) -> List[CategoryOut]:
    return await catalog_service.list_categories(
        session, active_only=active_only, search=search
    )


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    payload: CategoryCreate, ctx: CategoryCtx, session: SessionDep
) -> CategoryOut:
    category = await catalog_service.create_category(session, payload)
    await audit_service.record(
        session, ctx.admin, "category.create", "category", category.id,
        f"Membuat kategori {category.name_id}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return await _category_out(session, category)


async def _category_out(session, category: Category) -> CategoryOut:
    items = await catalog_service.list_categories(session)
    for item in items:
        if item.id == category.id:
            return item
    return CategoryOut.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int, payload: CategoryUpdate, ctx: CategoryCtx, session: SessionDep
) -> CategoryOut:
    category = await catalog_service.update_category(session, category_id, payload)
    await audit_service.record(
        session, ctx.admin, "category.update", "category", category.id,
        f"Memperbarui kategori {category.name_id}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return await _category_out(session, category)


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int, ctx: CategoryCtx, session: SessionDep
) -> MessageResponse:
    category = await catalog_service.get_category(session, category_id)
    name = category.name_id
    await catalog_service.delete_category(session, category_id)
    await audit_service.record(
        session, ctx.admin, "category.delete", "category", category_id,
        f"Menghapus kategori {name}", ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message="Kategori dihapus")


@router.get("/products", response_model=Page[ProductOut])
async def list_products(
    ctx: ProductCtx,
    session: SessionDep,
    category_id: Optional[int] = None,
    active_only: bool = False,
    featured: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[ProductOut]:
    items, total = await catalog_service.list_products(
        session,
        category_id=category_id,
        active_only=active_only,
        featured=featured,
        search=search,
        page=page,
        page_size=page_size,
    )
    return Page[ProductOut].build(items, total, page, page_size)


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int, ctx: ProductCtx, session: SessionDep
) -> ProductOut:
    product = await catalog_service.get_product(session, product_id)
    return await catalog_service.product_out(session, product)


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    payload: ProductCreate, ctx: ProductCtx, session: SessionDep
) -> ProductOut:
    product = await catalog_service.create_product(session, payload)
    await audit_service.record(
        session, ctx.admin, "product.create", "product", product.id,
        f"Membuat produk {product.name_id}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return await catalog_service.product_out(session, product)


@router.patch("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int, payload: ProductUpdate, ctx: ProductCtx, session: SessionDep
) -> ProductOut:
    product = await catalog_service.update_product(session, product_id, payload)
    await audit_service.record(
        session, ctx.admin, "product.update", "product", product.id,
        f"Memperbarui produk {product.name_id}", details=payload.model_dump(exclude_unset=True),
        ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return await catalog_service.product_out(session, product)


@router.delete("/products/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: int, ctx: ProductCtx, session: SessionDep
) -> MessageResponse:
    product = await catalog_service.get_product(session, product_id)
    name = product.name_id
    await catalog_service.delete_product(session, product_id)
    await audit_service.record(
        session, ctx.admin, "product.delete", "product", product_id,
        f"Menghapus produk {name}", ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message="Produk dihapus")


@router.post("/products/bulk-delete", response_model=MessageResponse)
async def bulk_delete_products(
    payload: BulkDeleteRequest, ctx: ProductCtx, session: SessionDep
) -> MessageResponse:
    deleted = 0
    for product_id in payload.ids:
        product = await session.get(Product, product_id)
        if product is None:
            continue
        await catalog_service.delete_product(session, product_id)
        deleted += 1
    await audit_service.record(
        session, ctx.admin, "product.bulk_delete", "product", None,
        f"Menghapus {deleted} produk", details=payload.ids, ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message=f"{deleted} produk dihapus")
