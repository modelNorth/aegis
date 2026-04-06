"""JWT authentication, API key validation, and tier-based rate limiting."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from aegis.core.constants import ApiTier
from aegis.core.exceptions import AuthenticationError


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def create_access_token(
    data: dict[str, Any],
    secret_key: str,
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(tier: ApiTier = ApiTier.FREE) -> tuple[str, str]:
    prefix_map = {
        ApiTier.FREE: "aegis_free",
        ApiTier.PRO: "aegis_pro",
        ApiTier.ENTERPRISE: "aegis_ent",
    }
    prefix = prefix_map.get(tier, "aegis")
    raw_key = secrets.token_urlsafe(32)
    api_key = f"{prefix}_{raw_key}"
    key_hash = hash_api_key(api_key)
    return api_key, key_hash


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    expected = mac.hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def get_tier_rate_limit(tier: ApiTier, limits: dict[str, int]) -> int:
    return {
        ApiTier.FREE: limits.get("free", 10),
        ApiTier.PRO: limits.get("pro", 100),
        ApiTier.ENTERPRISE: limits.get("enterprise", 1000),
    }.get(tier, 10)
