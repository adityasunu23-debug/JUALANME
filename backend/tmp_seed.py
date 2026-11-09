import asyncio
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.catalog import Category, Product
from app.models.stock import StockItem

async def main():
    async with SessionLocal() as s:
        cats = (await s.execute(select(func.count(Category.id)))).scalar()
        prods = (await s.execute(select(func.count(Product.id)))).scalar()
        stock = (await s.execute(select(func.count(StockItem.id)))).scalar()
        print(f"categories={cats} products={prods} stock={stock}")
        rows = (await s.execute(select(Product.id, Product.name_id, Product.price, Product.is_active))).all()
        for r in rows:
            print(" -", r)
asyncio.run(main())