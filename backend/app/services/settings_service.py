"""Runtime settings stored in the database and cached in Redis."""
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import settings as env

CACHE_KEY = "settings:all"
CACHE_TTL = 60

# (key, default value, group, label, type, is_secret)
DEFAULTS: List[Tuple[str, str, str, str, str, bool]] = [
    ("general.store_name", "Telegram Store", "general", "Nama Toko", "string", False),
    ("general.support_username", env.support_username, "general", "Username Support", "string", False),
    ("general.store_channel", env.store_channel, "general", "Channel Toko", "string", False),
    ("general.default_language", env.default_language, "general", "Bahasa Default", "string", False),
    ("general.maintenance_mode", "false", "general", "Mode Maintenance", "bool", False),
    ("payment.provider", env.payment_provider, "payment", "Payment Provider", "string", False),
    ("payment.cryptomus_merchant_uuid", env.cryptomus_merchant_uuid, "payment", "Cryptomus Merchant UUID", "string", True),
    ("payment.cryptomus_api_key", env.cryptomus_api_key, "payment", "Cryptomus API Key", "string", True),
    ("payment.network", env.cryptomus_network, "payment", "Jaringan Pembayaran", "string", False),
    ("payment.currency", env.payment_currency, "payment", "Mata Uang", "string", False),
    ("payment.invoice_lifetime_minutes", str(env.invoice_lifetime_minutes), "payment", "Masa Berlaku Invoice (menit)", "int", False),
    ("payment.min_confirmations", str(env.payment_min_confirmations), "payment", "Minimal Konfirmasi", "int", False),
    ("payment.auto_verify", "true", "payment", "Verifikasi Otomatis", "bool", False),
    ("delivery.auto_enabled", "true" if env.auto_delivery_enabled else "false", "delivery", "Pengiriman Otomatis", "bool", False),
    ("delivery.stock_low_threshold", str(env.stock_low_threshold), "delivery", "Ambang Stok Rendah", "int", False),
    ("notification.order_paid_enabled", "true", "notification", "Notifikasi Pembayaran", "bool", False),
    ("notification.admin_new_order_enabled", "true", "notification", "Notifikasi Pesanan Baru", "bool", False),
    ("notification.admin_telegram_id", "", "notification", "Telegram ID Admin Notifikasi", "string", False),
    ("security.webhook_require_signature", "true", "security", "Wajib Validasi Signature Webhook", "bool", False),
]


async def seed_defaults(session: AsyncSession) -> int:
    """Insert any missing setting row. Returns the number created."""
    from app.models.setting import Setting

    existing = await session.execute(select(Setting.key))
    known = {row[0] for row in existing.all()}
    created = 0
    for index, (key, value, group, label, value_type, is_secret) in enumerate(DEFAULTS):
        if key in known:
            continue
        session.add(
            Setting(
                key=key,
                value=value,
                group=group,
                label=label,
                value_type=value_type,
                is_secret=is_secret,
                sort_order=index,
            )
        )
        created += 1
    if created:
        await session.flush()
    return created


async def load_all(session: AsyncSession) -> Dict[str, str]:
    """Return every setting as a flat dict, cached for a short time."""
    cached = await cache.get_json(CACHE_KEY)
    if cached:
        return dict(cached)

    from app.models.setting import Setting

    result = await session.execute(select(Setting))
    values = {row.key: (row.value or "") for row in result.scalars().all()}
    await cache.set_json(CACHE_KEY, values, ttl=CACHE_TTL)
    return values


async def invalidate_cache() -> None:
    await cache.delete(CACHE_KEY)


async def get_value(session: AsyncSession, key: str, default: Optional[str] = None) -> str:
    values = await load_all(session)
    if key in values:
        return values[key]
    for default_key, value, *_ in DEFAULTS:
        if default_key == key:
            return value
    return default or ""


async def get_bool(session: AsyncSession, key: str, default: bool = False) -> bool:
    raw = (await get_value(session, key, "true" if default else "false")).strip().lower()
    return raw in ("1", "true", "yes", "on")


async def get_int(session: AsyncSession, key: str, default: int = 0) -> int:
    raw = await get_value(session, key, str(default))
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


async def set_value(session: AsyncSession, key: str, value: Any) -> None:
    from app.models.setting import Setting

    result = await session.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    text_value = "" if value is None else str(value)
    if row is None:
        session.add(Setting(key=key, value=text_value, group="general"))
    else:
        row.value = text_value
    await session.flush()
    await invalidate_cache()


# DB setting key -> attribute on the runtime Settings object.
RUNTIME_MAP: Dict[str, str] = {
    "payment.provider": "payment_provider",
    "payment.cryptomus_merchant_uuid": "cryptomus_merchant_uuid",
    "payment.cryptomus_api_key": "cryptomus_api_key",
    "payment.network": "cryptomus_network",
    "payment.currency": "payment_currency",
    "payment.invoice_lifetime_minutes": "invoice_lifetime_minutes",
    "payment.min_confirmations": "payment_min_confirmations",
    "delivery.auto_enabled": "auto_delivery_enabled",
    "delivery.stock_low_threshold": "stock_low_threshold",
}

INT_FIELDS = {"invoice_lifetime_minutes", "payment_min_confirmations", "stock_low_threshold"}
BOOL_FIELDS = {"auto_delivery_enabled"}


def apply_runtime_settings(values: Dict[str, str]) -> None:
    """Mirror dashboard-managed settings onto the runtime settings object.

    The payment gateway and delivery worker read from ``app.core.config.settings``;
    syncing here means an admin can change credentials or toggles without a
    redeploy, while environment variables stay as the fallback default.
    """
    for key, attribute in RUNTIME_MAP.items():
        raw = values.get(key)
        if raw is None or raw == "":
            continue
        if attribute in INT_FIELDS:
            try:
                setattr(env, attribute, int(float(raw)))
            except (TypeError, ValueError):
                continue
        elif attribute in BOOL_FIELDS:
            setattr(env, attribute, str(raw).strip().lower() in ("1", "true", "yes", "on"))
        else:
            setattr(env, attribute, str(raw))


async def sync_runtime(session: AsyncSession) -> None:
    """Load every setting and apply the ones the runtime cares about."""
    apply_runtime_settings(await load_all(session))


async def set_many(session: AsyncSession, values: Dict[str, Any]) -> int:
    if not values:
        return 0
    for key, value in values.items():
        await set_value(session, key, value)
    await invalidate_cache()
    await sync_runtime(session)
    return len(values)