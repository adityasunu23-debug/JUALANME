"""Admin management, audit log and settings schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AdminRole


class AdminCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: AdminRole = AdminRole.SUPPORT_ADMIN
    is_active: bool = True
    notes: Optional[str] = None


class AdminUpdate(BaseModel):
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str
    is_active: bool
    notes: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class RoleOption(BaseModel):
    value: str
    label: str
    permissions: List[str] = Field(default_factory=list)


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_id: Optional[int] = None
    admin_name: Optional[str] = None
    action: str
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    status: str = "SUCCESS"
    created_at: Optional[datetime] = None


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: Optional[str] = None
    group: str = "general"
    label: Optional[str] = None
    description: Optional[str] = None
    value_type: str = "string"
    is_secret: bool = False
    is_editable: bool = True
    sort_order: int = 0


class SettingUpdate(BaseModel):
    value: Optional[str] = None


class SettingsBulkUpdate(BaseModel):
    values: Dict[str, Any] = Field(default_factory=dict)


class ApiConfigOut(BaseModel):
    payment_provider: str
    cryptomus_configured: bool
    cryptomus_network: str
    payment_currency: str
    webhook_url: str
    webhook_secret_set: bool
    invoice_lifetime_minutes: int
    bot_configured: bool
    bot_username: str
    auto_delivery_enabled: bool
    min_confirmations: int


class NotificationTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    language: str
    title: Optional[str] = None
    body: str
    is_active: bool = True


class NotificationTemplateUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    is_active: Optional[bool] = None