"""
FastAPI Depends() helpers:
- Sliding-window rate limiter (per-IP, in-memory)
- Token extraction from Authorization: Bearer or httpOnly cookie
- get_current_user — raises 401 if missing/expired/invalid token
- get_optional_current_user — returns None when no token is present
- require_self — raises 403 if the authenticated user != the requested user_id
"""
from __future__ import annotations

import os
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
import jwt

from app.database import get_session
from app.models.user import User
from app.services.auth import decode_access_token

logger = logging.getLogger(__name__)

# Optional HTTPBearer — integrates with Swagger UI (auto_error=False so we handle 401 ourselves)
security_bearer = HTTPBearer(auto_error=False)

# ── In-memory sliding-window rate store ──────────────────────────────────────
# key → list of epoch timestamps within the current window
_rate_store: Dict[str, list] = defaultdict(list)
_rate_lock = Lock()


def rate_limit(max_calls: int, window_seconds: int):
    """
    Returns a FastAPI dependency that limits requests per IP.

    Uses a sliding window algorithm (O(n) eviction on each check).
    For production at scale, replace with Redis + lua script.

    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(5, 300))])
    """
    async def _check(request: Request) -> None:
        env = os.environ.get("ENVIRONMENT", "development")
        if env == "test" or os.environ.get("TESTING") == "1":
            return

        allowed_calls = max_calls * 20 if env == "development" else max_calls

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - window_seconds

        with _rate_lock:
            timestamps = _rate_store[ip]
            # Evict timestamps outside the window
            _rate_store[ip] = [t for t in timestamps if t > cutoff]

            if len(_rate_store[ip]) >= allowed_calls:
                logger.warning(
                    "RATE_LIMIT_EXCEEDED ip=%s path=%s calls=%d window=%ds",
                    ip, request.url.path, len(_rate_store[ip]), window_seconds,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Limit: {allowed_calls} per {window_seconds}s. Try again later.",
                    },
                    headers={"Retry-After": str(window_seconds)},
                )
            _rate_store[ip].append(now)

    return _check


# ── Token extraction ──────────────────────────────────────────────────────────

def extract_token_from_request(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Optional[str]:
    """
    Extract JWT from:
      1. Authorization: Bearer <token> header  (preferred — works with Swagger)
      2. access_token httpOnly cookie           (fallback for browser sessions)
    """
    if bearer and bearer.credentials:
        return bearer.credentials

    # Explicit header fallback (some clients set it manually)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return request.cookies.get("access_token")


# ── Token verification ────────────────────────────────────────────────────────

def verify_token(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Dict[str, Any]:
    """
    FastAPI Depends() helper — verifies the JWT and returns its payload.
    Raises 401 if the token is missing, expired, or has an invalid signature.
    """
    token = extract_token_from_request(request, bearer)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Authentication required.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return decode_access_token(token)
    except jwt.ExpiredSignatureError:
        logger.info("TOKEN_EXPIRED ip=%s path=%s", request.client.host if request.client else "?", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_EXPIRED", "message": "Session expired. Please sign in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, jwt.PyJWTError) as exc:
        logger.warning("INVALID_TOKEN ip=%s path=%s err=%s", request.client.host if request.client else "?", request.url.path, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_TOKEN", "message": "Invalid or tampered token."},
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── User resolution ───────────────────────────────────────────────────────────

def get_current_user(
    payload: Dict[str, Any] = Depends(verify_token),
    session: Session = Depends(get_session),
) -> User:
    """
    Resolve the authenticated User from the verified JWT payload.
    Raises 401 if the user ID in the token does not exist in the database
    (e.g., account was deleted after the token was issued).
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_TOKEN", "message": "Token missing identity claim."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "USER_NOT_FOUND", "message": "Account not found."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """
    Returns the authenticated User if a valid token is present; None otherwise.
    Raises 401 if a token IS provided but is expired or invalid
    (prevents silently downgrading authenticated requests to anonymous).
    """
    token = extract_token_from_request(request, bearer)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_EXPIRED", "message": "Session expired. Please sign in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, jwt.PyJWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_TOKEN", "message": "Invalid or tampered token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        return None
    return session.get(User, user_id)


# ── Ownership enforcement ─────────────────────────────────────────────────────

def require_self(requested_user_id: str, current_user: User) -> None:
    """
    Raise 403 Forbidden if the authenticated user is not the owner of the requested resource.
    Call this at the top of any endpoint that reads/writes data scoped to a specific user.

    Usage:
        require_self(user_id, current_user)
    """
    if requested_user_id == "me" or requested_user_id == current_user.id:
        return

    logger.warning(
        "IDOR_ATTEMPT authenticated_user=%s attempted_resource_owner=%s",
        current_user.id, requested_user_id,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "FORBIDDEN",
            "message": "You do not have permission to access this resource.",
        },
    )
