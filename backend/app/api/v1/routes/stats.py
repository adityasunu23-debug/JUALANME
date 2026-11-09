"""Dashboard statistics and revenue reports."""
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import AuthContext, SessionDep, require_permission
from app.schemas.stats import AnalyticsResponse, DashboardStats, RevenueReport
from app.services import stats_service

router = APIRouter(tags=["stats"])

DashboardCtx = Annotated[
    AuthContext, Depends(require_permission("dashboard.view"))
]
AnalyticsCtx = Annotated[
    AuthContext, Depends(require_permission("analytics.view"))
]
ReportsCtx = Annotated[AuthContext, Depends(require_permission("reports.view"))]


@router.get("/stats/dashboard", response_model=DashboardStats)
async def dashboard(ctx: DashboardCtx, session: SessionDep) -> DashboardStats:
    return await stats_service.dashboard_stats(session)


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(
    ctx: AnalyticsCtx,
    session: SessionDep,
    days: int = Query(30, ge=7, le=365),
) -> AnalyticsResponse:
    return await stats_service.analytics(session, days=days)


@router.get("/reports/revenue", response_model=RevenueReport)
async def revenue_report(
    ctx: ReportsCtx,
    session: SessionDep,
    period: str = Query("month"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> RevenueReport:
    return await stats_service.revenue_report(
        session, period=period, start_date=start_date, end_date=end_date
    )
