"""Audit logging for privileged actions."""
import json
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.audit import AuditLog


async def record(
    session: AsyncSession,
    admin: Optional[Admin],
    action: str,
    resource: Optional[str] = None,
    resource_id: Optional[Any] = None,
    description: Optional[str] = None,
    details: Optional[Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "SUCCESS",
    commit: bool = False,
) -> AuditLog:
    """Persist one audit entry. Never raises on serialisation issues."""
    payload: Optional[str] = None
    if details is not None:
        try:
            payload = json.dumps(details, default=str, ensure_ascii=False)[:8000]
        except (TypeError, ValueError):
            payload = str(details)[:8000]

    entry = AuditLog(
        admin_id=admin.id if admin else None,
        admin_telegram_id=admin.telegram_id if admin else None,
        admin_name=admin.display_name if admin else "system",
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        description=description,
        details=payload,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:256] or None,
        status=status,
    )
    session.add(entry)
    await session.flush()
    if commit:
        await session.commit()
    return entry