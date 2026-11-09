"""Catalogue management: categories, products and stock-aware serialisation."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.catalog import Category, Product
from app.models.enums import DeliveryType
from app.models.order import Order
from app.models.stock import StockItem
from app.schemas.catalog import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from app.services import stock_service


def _plain(values: Dict[str, Any]) -> Dict[str, Any]:
    return {key: (value.value if isinstance(value, Enum) else value) for key, value in values.items()}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "item"


async def _category_counts(
    session: AsyncSession, ids: Sequence[int]
) -> dict[int, int]:
    if not ids:
        return {}
    result = await session.execute(
        select(Product.category_id, func.count(Product.id))
        .where(Product.category_id.in_(list(ids)))
        .group_by(Product.category_id)
    )
    return {row[0]: int(row[1]) for row in result.all() if row[0] is not None}


def _category_out(category: Category, product_count: int) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        slug=category.slug,
        name_id=category.name_id,
        name_en=category.name_en,
        description_id=category.description_id,
        description_en=category.description_en,
        icon=category.icon,
        sort_order=category.sort_order,
        is_active=category.is_active,
        product_count=product_count,
        created_at=category.created_at,
    )


async def list_categories(
    session: AsyncSession,
    *,
    active_only: bool = False,
    search: Optional[str] = None,
) -> List[CategoryOut]:
    query = select(Category)
    if active_only:
        query = query.where(Category.is_active.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(Category.name_id.ilike(pattern), Category.name_en.ilike(pattern))
        )
    query = query.order_by(Category.sort_order.asc(), Category.id.asc())
    result = await session.execute(query)
    categories = list(result.scalars().all())
    counts = await _category_counts(session, [c.id for c in categories])
    return [_category_out(c, counts.get(c.id, 0)) for c in categories]


async def get_category(session: AsyncSession, category_id: int) -> Category:
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFoundError("Kategori tidak ditemukan")
    return category


async def create_category(session: AsyncSession, data: CategoryCreate) -> Category:
    slug = data.slug or slugify(data.name_en or data.name_id)
    existing = await session.execute(select(Category.id).where(Category.slug == slug))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(f"Slug kategori '{slug}' sudah digunakan")
    category = Category(**_plain(data.model_dump(exclude={"stock"})))
    category.slug = slug
    session.add(category)
    await session.flush()
    return category


async def update_category(
    session: AsyncSession, category_id: int, data: CategoryUpdate
) -> Category:
    category = await get_category(session, category_id)
    values = data.model_dump(exclude_unset=True)
    if "slug" in values and values["slug"]:
        duplicate = await session.execute(
            select(Category.id).where(
                Category.slug == values["slug"], Category.id != category_id
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise ConflictError("Slug kategori sudah digunakan")
    for key, value in values.items():
        setattr(category, key, value)
    await session.flush()
    return category


async def delete_category(session: AsyncSession, category_id: int) -> None:
    category = await get_category(session, category_id)
    product_count = await session.execute(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    )
    if int(product_count.scalar() or 0) > 0:
        raise ConflictError(
            "Kategori masih memiliki produk. Pindahkan atau hapus produk terlebih dahulu."
        )
    await session.delete(category)
    await session.flush()


def _product_out(
    product: Product, available: int, sold: int, category_name: Optional[str]
) -> ProductOut:
    return ProductOut(
        id=product.id,
        category_id=product.category_id,
        sku=product.sku,
        name_id=product.name_id,
        name_en=product.name_en,
        description_id=product.description_id,
        description_en=product.description_en,
        price=float(product.price),
        compare_price=float(product.compare_price) if product.compare_price else None,
        currency=product.currency,
        delivery_type=DeliveryType(product.delivery_type),
        image_url=product.image_url,
        min_quantity=product.min_quantity,
        max_quantity=product.max_quantity,
        is_active=product.is_active,
        is_featured=product.is_featured,
        sort_order=product.sort_order,
        delivery_instructions=product.delivery_instructions,
        sold_count=product.sold_count,
        stock_available=available,
        stock_sold=sold,
        category_name=category_name,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def product_out(session: AsyncSession, product: Product) -> ProductOut:
    available = await stock_service.count_available(session, product.id)
    sold = await stock_service.count_sold(session, product.id)
    category_name = None
    if product.category_id:
        name = await session.execute(
            select(Category.name_id).where(Category.id == product.category_id)
        )
        category_name = name.scalar_one_or_none()
    return _product_out(product, available, sold, category_name)


async def list_products(
    session: AsyncSession,
    *,
    category_id: Optional[int] = None,
    active_only: bool = False,
    featured: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[ProductOut], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    conditions = []
    if category_id:
        conditions.append(Product.category_id == category_id)
    if active_only:
        conditions.append(Product.is_active.is_(True))
    if featured is not None:
        conditions.append(Product.is_featured.is_(featured))
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Product.name_id.ilike(pattern),
                Product.name_en.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    count_query = select(func.count(Product.id))
    query = select(Product).order_by(Product.sort_order.asc(), Product.id.desc())
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    products = list(result.scalars().all())

    available = await stock_service.available_map(session, [p.id for p in products])
    sold = await stock_service.sold_map(session, [p.id for p in products])
    category_ids = {p.category_id for p in products if p.category_id}
    names: dict[int, str] = {}
    if category_ids:
        name_rows = await session.execute(
            select(Category.id, Category.name_id).where(Category.id.in_(category_ids))
        )
        names = {row[0]: row[1] for row in name_rows.all()}
    items = [
        _product_out(
            product,
            available.get(product.id, 0),
            sold.get(product.id, 0),
            names.get(product.category_id) if product.category_id else None,
        )
        for product in products
    ]
    return items, total


async def get_product(session: AsyncSession, product_id: int) -> Product:
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise NotFoundError("Produk tidak ditemukan")
    return product


async def create_product(
    session: AsyncSession, data: ProductCreate
) -> Product:
    if data.category_id:
        await get_category(session, data.category_id)
    payload = _plain(data.model_dump(exclude={"stock"}))
    product = Product(**payload)
    session.add(product)
    await session.flush()
    if data.stock:
        await stock_service.add_stock(
            session,
            product.id,
            data.stock,
            source="initial",
            deduplicate=True,
        )
        await session.flush()
    return product


async def update_product(
    session: AsyncSession, product_id: int, data: ProductUpdate
) -> Product:
    product = await get_product(session, product_id)
    values = _plain(data.model_dump(exclude_unset=True))
    if "category_id" in values and values["category_id"]:
        await get_category(session, values["category_id"])
    for key, value in values.items():
        setattr(product, key, value)
    await session.flush()
    return product


async def delete_product(session: AsyncSession, product_id: int) -> None:
    product = await get_product(session, product_id)
    order_count = await session.execute(
        select(func.count(Order.id)).where(Order.product_id == product_id)
    )
    if int(order_count.scalar() or 0) > 0:
        raise ConflictError(
            "Produk sudah memiliki pesanan. Nonaktifkan produk alih-alih menghapus."
        )
    await session.delete(product)
    await session.flush()


async def stock_summaries(session: AsyncSession) -> List[dict]:
    products = await session.execute(select(Product).order_by(Product.id.asc()))
    rows = list(products.scalars().all())
    available = await stock_service.available_map(session, [p.id for p in rows])
    sold = await stock_service.sold_map(session, [p.id for p in rows])
    return [
        {
            "product_id": product.id,
            "product_name": product.name_id,
            "delivery_type": product.delivery_type,
            "available": available.get(product.id, 0),
            "sold": sold.get(product.id, 0),
            "total": available.get(product.id, 0) + sold.get(product.id, 0),
        }
        for product in rows
    ]
