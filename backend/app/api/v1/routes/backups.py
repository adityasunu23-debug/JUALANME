"""Database backup endpoints (owner only)."""
from typing import Annotated, List

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.deps import AuthContext, SessionDep, require_owner
from app.schemas.stats import BackupResult
from app.services import audit_service, backup_service

router = APIRouter(prefix="/backups", tags=["backups"])

OwnerCtx = Annotated[AuthContext, Depends(require_owner())]


@router.get("", response_model=List[BackupResult])
async def list_backups(ctx: OwnerCtx) -> List[BackupResult]:
    return backup_service.list_backups()


@router.post("", response_model=BackupResult)
async def create_backup(ctx: OwnerCtx, session: SessionDep) -> BackupResult:
    result = await backup_service.create_backup(session)
    await audit_service.record(
        session, ctx.admin, "backup.create", "backup", result.filename,
        f"Membuat backup {result.filename}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return result


@router.get("/{filename}")
async def download_backup(filename: str, ctx: OwnerCtx) -> FileResponse:
    path = backup_service.backup_path(filename)
    return FileResponse(path, media_type="application/json", filename=filename)
