"""JWT issuing/validation and Telegram Login Widget signature checks."""
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.core.config import settings

TELEGRAM_LOGIN_MAX_AGE_SECONDS = 86400


class TokenError(Exception):
    """Raised when a JWT cannot be trusted."""


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """Issue a signed JWT for an admin session."""
    minutes = expires_minutes or settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify a JWT and return its claims."""
    try:
        return jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token kedaluwarsa") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token tidak valid") from exc


def verify_telegram_login(data: Dict[str, Any], bot_token: str) -> bool:
    """Validate the hash produced by the Telegram Login Widget.

    Algorithm (Telegram docs): secret_key = SHA256(bot_token);
    check_hash = HMAC_SHA256(data_check_string, secret_key).
    """
    if not bot_token:
        return False
    received_hash = data.get("hash")
    if not received_hash:
        return False

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(data.items())
        if key != "hash" and value is not None
    )
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    computed = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed, str(received_hash)):
        return False

    auth_date = data.get("auth_date")
    try:
        issued_at = int(auth_date)
    except (TypeError, ValueError):
        return False
    return (time.time() - issued_at) <= TELEGRAM_LOGIN_MAX_AGE_SECONDS


def build_telegram_data_check_string(data: Dict[str, Any]) -> str:
    """Exposed for tests."""
    return "\n".join(
        f"{key}={value}"
        for key, value in sorted(data.items())
        if key != "hash" and value is not None
    )


def canonical_json(payload: Any) -> str:
    """Deterministic JSON string used when computing webhook payload hashes."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)