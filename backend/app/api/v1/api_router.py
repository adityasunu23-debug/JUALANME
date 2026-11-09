"""Aggregate every v1 route under a single router."""
from fastapi import APIRouter

from app.api.v1.routes import (
    admins,
    auth,
    backups,
    broadcasts,
    catalog,
    customers,
    deliveries,
    health,
    orders,
    payments,
    settings,
    stats,
    stock,
    tickets,
    vouchers,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admins.router)
api_router.include_router(catalog.router)
api_router.include_router(stock.router)
api_router.include_router(orders.router)
api_router.include_router(deliveries.router)
api_router.include_router(payments.router)
api_router.include_router(vouchers.router)
api_router.include_router(broadcasts.router)
api_router.include_router(customers.router)
api_router.include_router(tickets.router)
api_router.include_router(settings.router)
api_router.include_router(stats.router)
api_router.include_router(backups.router)
