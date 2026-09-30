"""安全：密码哈希（PBKDF2-SHA256，标准库实现）与 JWT 签发/校验"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

# 哈希存储格式：pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>
_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return secrets.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    """subject 为 user id 字符串"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """校验并返回 subject；无效/过期返回 None"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
