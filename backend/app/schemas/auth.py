"""Authentication payloads."""
from typing import List, Optional

from pydantic import BaseModel, Field


class TelegramLoginRequest(BaseModel):
    """Payload forwarded from the Telegram Login Widget."""

    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class DevLoginRequest(BaseModel):
    telegram_id: int = Field(..., description="Seeded admin telegram id (dev only)")


class AdminProfile(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str
    is_active: bool
    permissions: List[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: AdminProfile