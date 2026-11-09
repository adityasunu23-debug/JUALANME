"""Bot routers."""
from aiogram import Router

from app.bot.handlers import catalog, orders, payments, start, support


def build_router() -> Router:
    root = Router(name="customer")
    root.include_router(start.router)
    root.include_router(catalog.router)
    root.include_router(orders.router)
    root.include_router(payments.router)
    root.include_router(support.router)
    return root


__all__ = ["build_router"]
