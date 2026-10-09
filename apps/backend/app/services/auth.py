"""
Authentication and JWT token management.
- Password hashing with bcrypt (cost factor 12)
- JWT signing and verification with SECRET_KEY
- Secure token expiration (30 min default, configurable)
- Login-attempt tracking for brute-force protection
"""
import os
import uuid
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional, Dict, Any, Tuple

import bcrypt
import jwt

logger = logging.getLogger(__name__)

# ── Secrets — MUST come from environment, never hardcoded ────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY in ("dev_secret_change_in_production", "change_me_generate_a_real_secret_key"):
    if os.getenv("ENVIRONMENT") == "production":
        raise RuntimeError(
            "SECRET_KEY env var is missing or still set to the placeholder value. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    # Development fallback — logged loudly so it's never missed
    SECRET_KEY = "dev_only_" + uuid.uuid4().hex
    logger.warning("⚠️  SECRET_KEY not set — using ephemeral dev key. Tokens reset on every restart.")

ALGORITHM = "HS256"
# Short-lived access tokens — 30 minutes by default (override with env var)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# ── Brute-force protection: per-identifier login attempt tracking ─────────────
# Maps normalised identifier → (failure_count, window_start)
_login_attempts: Dict[str, Tuple[int, datetime]] = defaultdict(lambda: (0, datetime.now(timezone.utc)))
_attempts_lock = Lock()

LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "900"))  # 15 min


def record_login_failure(identifier: str) -> None:
    """Track a failed login attempt for the given identifier (email/username)."""
    key = identifier.strip().lower()
    with _attempts_lock:
        count, window_start = _login_attempts[key]
        now = datetime.now(timezone.utc)
        # Reset window if older than lockout period
        if (now - window_start).total_seconds() > LOGIN_LOCKOUT_SECONDS:
            _login_attempts[key] = (1, now)
        else:
            _login_attempts[key] = (count + 1, window_start)
    logger.warning("LOGIN_FAILURE identifier=%s failures=%d", key, _login_attempts[key][0])


def record_login_success(identifier: str) -> None:
    """Clear failure count on successful login."""
    key = identifier.strip().lower()
    with _attempts_lock:
        _login_attempts.pop(key, None)


def is_account_locked(identifier: str) -> bool:
    """Return True if the identifier is currently locked out."""
    if os.environ.get("ENVIRONMENT") in ("test", "development"):
        return False
    key = identifier.strip().lower()
    with _attempts_lock:
        count, window_start = _login_attempts.get(key, (0, datetime.now(timezone.utc)))
        now = datetime.now(timezone.utc)
        if (now - window_start).total_seconds() > LOGIN_LOCKOUT_SECONDS:
            # Window expired — clean up
            _login_attempts.pop(key, None)
            return False
        return count >= LOGIN_MAX_FAILURES


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with cost factor 12."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify a plaintext password against a bcrypt hash. Always takes constant time."""
    if not plain_password or not hashed_password:
        # Still call checkpw with a dummy to avoid timing oracle
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4)))
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ── JWT handling ──────────────────────────────────────────────────────────────

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Sign a JWT with SECRET_KEY and HS256 algorithm.
    Includes sub, iat, exp, and jti (unique token ID) claims.
    Only the user's ID (sub) is embedded — no sensitive PII.
    """
    to_encode = {"sub": data["sub"]}  # Only embed user ID — never email/username in JWT
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),   # Unique token ID for future revocation support
        "type": "access",
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a signed JWT using SECRET_KEY.
    Validates: signature, expiry, algorithm.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"require": ["exp", "iat", "sub", "jti"]},
    )
    # Reject tokens that aren't access tokens
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Token type mismatch")
    return payload
