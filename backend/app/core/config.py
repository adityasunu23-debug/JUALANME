"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ---------- General ----------
    app_name: str = "Telegram Store"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    default_language: str = "id"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---------- Database ----------
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"
    db_echo: bool = False

    # ---------- Redis ----------
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True

    # ---------- Telegram ----------
    bot_token: str = ""
    bot_username: str = "your_store_bot"
    bot_webhook_url: str = ""
    bot_webhook_secret: str = ""
    support_username: str = "@your_support"
    store_channel: str = ""

    # ---------- Admin auth ----------
    admin_telegram_ids: str = ""
    dev_login_enabled: bool = True
    dev_login_telegram_id: int = 123456789

    # ---------- Payments ----------
    payment_provider: str = "cryptomus"
    cryptomus_merchant_uuid: str = ""
    cryptomus_api_key: str = ""
    cryptomus_api_url: str = "https://api.cryptomus.com/v1"
    cryptomus_network: str = "bep20"
    payment_currency: str = "USDT"
    invoice_lifetime_minutes: int = 30
    payment_min_confirmations: int = 1
    webhook_base_url: str = "http://localhost:8000"
    dashboard_base_url: str = "http://localhost:3000"

    # ---------- Store behaviour ----------
    order_expiry_minutes: int = 30
    auto_delivery_enabled: bool = True
    stock_low_threshold: int = 5

    # ---------- Backup ----------
    backup_dir: str = "./data/backups"

    # ---------- Background jobs ----------
    enable_workers: bool = True

    @field_validator("app_env")
    @classmethod
    def _normalize_env(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def admin_telegram_id_list(self) -> List[int]:
        ids: List[int] = []
        for raw in self.admin_telegram_ids.split(","):
            raw = raw.strip()
            if raw.isdigit():
                ids.append(int(raw))
        return ids

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
