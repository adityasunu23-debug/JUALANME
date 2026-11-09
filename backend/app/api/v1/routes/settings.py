"""Runtime settings, API configuration and notification templates."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import AuthContext, SessionDep, require_permission
from app.core.exceptions import NotFoundError
from app.models.setting import NotificationTemplate, Setting
from app.schemas.admin import (
    ApiConfigOut,
    NotificationTemplateOut,
    NotificationTemplateUpdate,
    SettingOut,
    SettingsBulkUpdate,
)
from app.schemas.common import MessageResponse
from app.services import audit_service, settings_service

router = APIRouter(prefix="/settings", tags=["settings"])

SettingsCtx = Annotated[
    AuthContext, Depends(require_permission("settings.manage"))
]

SECRET_MASK = "********"


def _setting_out(row: Setting) -> SettingOut:
    value = row.value
    if row.is_secret and value:
        value = SECRET_MASK
    return SettingOut(
        id=row.id,
        key=row.key,
        value=value,
        group=row.group,
        label=row.label,
        description=row.description,
        value_type=row.value_type,
        is_secret=row.is_secret,
        is_editable=row.is_editable,
        sort_order=row.sort_order,
    )


@router.get("", response_model=List[SettingOut])
async def list_settings(ctx: SettingsCtx, session: SessionDep) -> List[SettingOut]:
    result = await session.execute(
        select(Setting).order_by(Setting.group.asc(), Setting.sort_order.asc())
    )
    return [_setting_out(row) for row in result.scalars().all()]


@router.patch("", response_model=MessageResponse)
async def update_settings(
    payload: SettingsBulkUpdate, ctx: SettingsCtx, session: SessionDep
) -> MessageResponse:
    allowed = {
        key: value
        for key, value in payload.values.items()
        if value not in (None, SECRET_MASK)
    }
    if not allowed:
        raise HTTPException(status_code=400, detail="Tidak ada nilai yang diubah")
    result = await session.execute(
        select(Setting).where(Setting.key.in_(list(allowed.keys())))
    )
    editable = {row.key for row in result.scalars().all() if row.is_editable}
    final = {key: value for key, value in allowed.items() if key in editable}
    if not final:
        raise HTTPException(status_code=400, detail="Tidak ada setting yang dapat diubah")
    await settings_service.set_many(session, final)
    await audit_service.record(
        session, ctx.admin, "settings.update", "settings", None,
        f"Memperbarui {len(final)} setting", details=final, ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message=f"{len(final)} setting diperbarui")


@router.get("/api-config", response_model=ApiConfigOut)
async def api_config(ctx: SettingsCtx) -> ApiConfigOut:
    return ApiConfigOut(
        payment_provider=settings.payment_provider,
        cryptomus_configured=bool(
            settings.cryptomus_merchant_uuid and settings.cryptomus_api_key
        ),
        cryptomus_network=settings.cryptomus_network,
        payment_currency=settings.payment_currency,
        webhook_url=f"{settings.webhook_base_url.rstrip('/')}/api/v1/payments/webhook/{settings.payment_provider}",
        webhook_secret_set=bool(settings.bot_webhook_secret),
        invoice_lifetime_minutes=settings.invoice_lifetime_minutes,
        bot_configured=bool(settings.bot_token),
        bot_username=settings.bot_username,
        auto_delivery_enabled=settings.auto_delivery_enabled,
        min_confirmations=settings.payment_min_confirmations,
    )


@router.get("/templates", response_model=List[NotificationTemplateOut])
async def list_templates(
    ctx: SettingsCtx, session: SessionDep
) -> List[NotificationTemplateOut]:
    result = await session.execute(
        select(NotificationTemplate).order_by(
            NotificationTemplate.code.asc(), NotificationTemplate.language.asc()
        )
    )
    return [
        NotificationTemplateOut.model_validate(row)
        for row in result.scalars().all()
    ]


@router.patch("/templates/{template_id}", response_model=NotificationTemplateOut)
async def update_template(
    template_id: int,
    payload: NotificationTemplateUpdate,
    ctx: SettingsCtx,
    session: SessionDep,
) -> NotificationTemplateOut:
    template = await session.get(NotificationTemplate, template_id)
    if template is None:
        raise NotFoundError("Template tidak ditemukan")
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        if value is not None:
            setattr(template, key, value)
    await session.flush()
    await audit_service.record(
        session, ctx.admin, "settings.template", "notification_template", template.id,
        f"Memperbarui template {template.code}/{template.language}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return NotificationTemplateOut.model_validate(template)
