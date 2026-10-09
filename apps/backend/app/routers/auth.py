"""
Authentication router.

POST /api/auth/login  — Authenticate with username/email + password.
                        Rate-limited: 5 attempts / 5 min per IP.
                        Locks out after 5 failures per identifier for 15 min.
POST /api/auth/logout — Clears httpOnly cookie.
GET  /api/auth/me     — Current user info (requires valid JWT).

Security notes:
- Identical error message for "user not found" and "wrong password"
  (prevents user-enumeration attacks).
- Login failures are logged for SIEM / anomaly detection.
- JWT set in httpOnly, SameSite=Lax cookie AND returned in body for API clients.
- Cookie is Secure=True in production (requires HTTPS).
- Docs always expose the /api prefix routes; legacy /login kept for compat.
"""
import os
import logging
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from sqlmodel import Session, select, or_

from app.database import get_session
from app.models.user import User
from app.schemas import LoginRequest, TokenResponse, UserResponse
from app.services.auth import (
    verify_password,
    create_access_token,
    record_login_failure,
    record_login_success,
    is_account_locked,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.services.tiers import get_tier
from app.dependencies import get_current_user, rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

COOKIE_NAME = "access_token"
IS_PRODUCTION = os.getenv("ENVIRONMENT") == "production"
TOKEN_EXPIRY_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60

# Rate limit: 5 login attempts per IP per 5 minutes
_login_rate_limit = rate_limit(max_calls=5, window_seconds=300)


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the httpOnly auth cookie with appropriate security flags."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=TOKEN_EXPIRY_SECONDS,
        expires=TOKEN_EXPIRY_SECONDS,
        samesite="lax",
        secure=IS_PRODUCTION,   # Must be True in production (HTTPS only)
        path="/",
    )


def _build_user_response(user: User) -> UserResponse:
    return UserResponse(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username,
        total_points=user.total_points,
        current_streak=user.current_streak,
        tier=get_tier(user.total_points),
        created_at=user.created_at,
    )


def authenticate_and_create_token(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Session,
) -> TokenResponse:
    """
    Core login logic.
    1. Resolve identifier (username or email)
    2. Check lockout status
    3. Verify bcrypt password (constant-time)
    4. On success: clear failure count, sign JWT, set cookie
    5. On failure: record failure, return identical 401 (no user-enumeration)
    """
    ip = request.client.host if request.client else "unknown"

    identifier = (body.identifier or body.username or body.email or "").strip().lower()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MISSING_IDENTIFIER", "message": "Username or email is required."},
        )

    # Check if this identifier is locked out (too many recent failures)
    if is_account_locked(identifier):
        logger.warning("LOGIN_LOCKED ip=%s identifier=%s", ip, identifier)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "ACCOUNT_LOCKED",
                "message": "Too many failed login attempts. Please try again in 15 minutes.",
            },
            headers={"Retry-After": "900"},
        )

    # Find user — intentionally use a single query to prevent timing difference
    user = session.exec(
        select(User).where(
            or_(
                User.email.ilike(identifier),
                User.username.ilike(identifier),
            )
        )
    ).first()

    # Constant-time comparison: always call verify_password even if user not found
    password_ok = verify_password(body.password, user.hashed_password if user else None)

    if not user or not password_ok:
        record_login_failure(identifier)
        logger.warning("LOGIN_FAILED ip=%s identifier=%s", ip, identifier)
        # Identical message — prevents user-enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_CREDENTIALS", "message": "Invalid username/email or password."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Success ───────────────────────────────────────────────────────────────
    record_login_success(identifier)
    logger.info("LOGIN_SUCCESS ip=%s user_id=%s", ip, user.id)

    # JWT contains ONLY the user ID — no PII in the token
    token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    _set_auth_cookie(response, token)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=TOKEN_EXPIRY_SECONDS,
        user=_build_user_response(user),
    )


# ── POST /api/auth/login ──────────────────────────────────────────────────────
@router.post(
    "/api/auth/login",
    response_model=TokenResponse,
    dependencies=[Depends(_login_rate_limit)],
)
def login_api(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """Authenticate with username/email and password, receive JWT & httpOnly cookie."""
    return authenticate_and_create_token(body, request, response, session)


# Legacy path kept for any clients using /login directly
@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(_login_rate_limit)],
    include_in_schema=False,  # Hidden from docs — use /api/auth/login
)
def login_root(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    return authenticate_and_create_token(body, request, response, session)


# ── POST /api/auth/logout ─────────────────────────────────────────────────────
@router.post("/api/auth/logout")
@router.post("/logout", include_in_schema=False)
def logout(response: Response):
    """Clear httpOnly cookie to log the user out."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        samesite="lax",
        secure=IS_PRODUCTION,
        httponly=True,
    )
    return {"message": "Logged out successfully."}


# ── GET /api/auth/me ──────────────────────────────────────────────────────────
@router.get("/api/auth/me", response_model=UserResponse)
def get_auth_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return _build_user_response(current_user)
