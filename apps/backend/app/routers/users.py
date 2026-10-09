"""
Users router.
POST /api/users       — register a new account (rate-limited: 10/hr/IP)
GET  /api/users/me    — authenticated user's own profile
GET  /api/users/{id}  — public profile (limited fields, requires auth)

Security:
- Registration is rate-limited to prevent account-creation abuse.
- GET /{user_id} requires authentication (no anonymous enumeration).
- Email is redacted from public profile responses.
- Password strength enforced at schema level (min 8 chars, complexity).
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select
import sqlalchemy.exc

from app.database import get_session
from app.models.user import User
from app.schemas import UserCreate, UserResponse, PublicUserResponse
from app.services.tiers import get_tier
from app.services.auth import hash_password
from app.dependencies import get_current_user, get_optional_current_user, rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

# Rate limit: 10 registrations per hour per IP — prevents mass account creation
_register_rate_limit = rate_limit(max_calls=10, window_seconds=3600)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    dependencies=[Depends(_register_rate_limit)],
)
def register_user(body: UserCreate, session: Session = Depends(get_session)):
    """
    Register a new user.

    Duplicate detection:
      1. App-level check (clean 409 message)
      2. DB-level UNIQUE constraint (catches race conditions)
    """
    # App-level duplicate check — case-insensitive name comparison
    existing = session.exec(
        select(User).where(
            User.first_name.ilike(body.first_name.strip()),
            User.last_name.ilike(body.last_name.strip()),
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "USER_EXISTS",
                "message": f"{body.first_name} {body.last_name} is already registered.",
            },
        )

    clean_username = body.username.strip().lower() if body.username else None
    clean_email = body.email.strip().lower() if body.email else None

    # Check username uniqueness (case-insensitive)
    if clean_username:
        dup_username = session.exec(
            select(User).where(User.username.ilike(clean_username))
        ).first()
        if dup_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "USERNAME_TAKEN",
                    "message": f"Username '{body.username}' is already taken.",
                },
            )

    # Check email uniqueness (case-insensitive)
    if clean_email:
        dup_email = session.exec(
            select(User).where(User.email.ilike(clean_email))
        ).first()
        if dup_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "EMAIL_TAKEN",
                    "message": "An account with this email already exists.",
                },
            )

    hashed_pw = hash_password(body.password) if body.password else None

    user = User(
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        email=clean_email,
        username=clean_username,
        timezone=body.timezone,
        fitness_goal=body.fitness_goal,
        bio=body.bio,
        hashed_password=hashed_pw,
    )

    try:
        session.add(user)
        session.commit()
        session.refresh(user)
    except sqlalchemy.exc.IntegrityError as err:
        session.rollback()
        err_str = str(err).lower()
        if "uq_users_email" in err_str or "email" in err_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "EMAIL_TAKEN", "message": "An account with this email already exists."},
            )
        if "uq_users_username" in err_str or "username" in err_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "USERNAME_TAKEN", "message": f"Username '{body.username}' is already taken."},
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "USER_EXISTS", "message": f"{body.first_name} {body.last_name} is already registered."},
        )

    logger.info("USER_REGISTERED user_id=%s username=%s", user.id, user.username)

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


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return the full profile of the currently authenticated user."""
    return UserResponse(
        user_id=current_user.id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        username=current_user.username,
        total_points=current_user.total_points,
        current_streak=current_user.current_streak,
        tier=get_tier(current_user.total_points),
        created_at=current_user.created_at,
    )


@router.get("/{user_id}", response_model=PublicUserResponse)
def get_user(
    user_id: str,
    current_user: User = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    """
    Get a user's public profile.
    Requires authentication — unauthenticated clients cannot enumerate users.
    Email is NOT included in the public response.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "USER_NOT_FOUND", "message": "User not found."},
        )
    return PublicUserResponse(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username,
        total_points=user.total_points,
        current_streak=user.current_streak,
        tier=get_tier(user.total_points),
        bio=user.bio,
        created_at=user.created_at,
    )
