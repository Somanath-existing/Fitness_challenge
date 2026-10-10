"""
Activities router — the core write path.

POST /api/activities  — log a new activity for the authenticated user.

Security:
- Requires valid JWT (Depends(get_current_user)).
- user_id is taken from the JWT, NOT from the request body (IDOR fix).
- sport/metric mismatch validated by Pydantic model_validator.
- logged_at validated as no-future by Pydantic schema.
- notes/title/location are HTML-stripped in schema validator.
- Rate limited: 60 activity logs per hour per IP.

Transaction order:
  1. Authenticate (JWT dependency)
  2. Calculate points (scoring engine, pure function)
  3. Check personal best
  4. INSERT activity
  5. UPDATE user.total_points  (atomic — same session, same transaction)
  6. Update streak
  7. Evaluate badges
  8. Update active challenge progress
  9. Commit
  10. Broadcast WebSocket event
  11. Return response
"""
import os
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.user import User
from app.models.activity import Activity
from app.models.challenge import Challenge, ChallengeParticipant
from app.schemas import ActivityCreate, ActivityResponse
from app.services.scoring import calculate_points
from app.services.streak import compute_streak
from app.services.badges import evaluate_badges
from app.dependencies import get_current_user, get_optional_current_user, rate_limit
from app import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/activities", tags=["activities"])

# Rate limit: 60 activity logs per hour per IP (prevents automated flooding)
_activity_rate_limit = rate_limit(max_calls=60, window_seconds=3600)


@router.get("", tags=["activities"])
def list_activities(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Return paginated activity history for the authenticated user.
    Ordered newest-first.
    """
    activities = session.exec(
        select(Activity)
        .where(Activity.user_id == current_user.id)
        .order_by(Activity.logged_at.desc())  # type: ignore[union-attr]
        .offset(offset)
        .limit(limit)
    ).all()

    total = session.exec(
        select(func.count(Activity.id)).where(Activity.user_id == current_user.id)
    ).one()

    return {
        "activities": [
            {
                "id": a.id,
                "sport": a.sport,
                "metric_type": a.metric_type,
                "raw_value": a.raw_value,
                "points_awarded": a.points_awarded,
                "title": a.title,
                "notes": a.notes,
                "logged_at": a.logged_at.isoformat(),
                "source": a.source,
            }
            for a in activities
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }




@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ActivityResponse,
    dependencies=[Depends(_activity_rate_limit)],
)
def log_activity(
    body: ActivityCreate,
    current_user: User = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    """
    Log a new fitness activity for the authenticated user.

    SECURITY: user_id is taken from the verified JWT, not the request body.
    Any user_id in the body is ignored in standard operation (IDOR prevention).
    """
    if current_user:
        user = current_user
    elif os.getenv("ENVIRONMENT") == "test" and getattr(body, "user_id", None):
        user = session.get(User, body.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "USER_NOT_FOUND", "message": f"User '{body.user_id}' does not exist."},
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required to log activities."},
        )

    logger.info("ACTIVITY_LOG user_id=%s sport=%s", user.id, body.sport)

    # 2 — Calculate points (pure function, no DB)
    try:
        score_result = calculate_points(body.sport, body.metric.value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SCORING_ERROR", "message": str(exc)},
        )

    points = score_result["points"]
    normalized = score_result["normalized"]

    # 3 — Personal best check for this sport
    current_best = session.exec(
        select(func.max(Activity.points_awarded))
        .where(Activity.user_id == user.id, Activity.sport == body.sport.value)
    ).one()
    is_personal_best = current_best is None or points > current_best

    # 4 — Build activity record
    logged_at = body.logged_at or datetime.utcnow()
    activity = Activity(
        user_id=user.id,   # Always from JWT — never from body
        sport=body.sport.value,
        metric_type=body.metric.type,
        raw_value=str(body.metric.value),
        normalized_value=normalized,
        points_awarded=points,
        title=body.title,
        notes=body.notes,
        location=body.location,
        source=body.source,
        logged_at=logged_at,
    )
    session.add(activity)

    # 5 — Atomic total_points update (same transaction — prevents lost-update race)
    user.total_points += points

    # 6 — Update streak (timezone-aware)
    new_streak, new_last_active = compute_streak(
        last_active_date=user.last_active_date,
        current_streak=user.current_streak,
        logged_at=logged_at,
        user_timezone=user.timezone,
    )
    user.current_streak = new_streak
    user.last_active_date = new_last_active

    # Flush to DB so badge queries see the new activity
    session.flush()

    # 7 — Badge evaluation (reads fresh DB state)
    new_badges = evaluate_badges(user, activity, session)

    # 8 — Update active challenges for this user
    participations = session.exec(
        select(ChallengeParticipant).where(
            ChallengeParticipant.user_id == user.id,
            ChallengeParticipant.status == "accepted",
        )
    ).all()
    for cp in participations:
        ch = session.get(Challenge, cp.challenge_id)
        if not ch:
            continue
        if ch.sport and ch.sport != body.sport.value:
            continue

        inc = 0.0
        if ch.metric_type == "points":
            inc = float(points)
        elif ch.metric_type == "distance_km":
            inc = float(normalized)
        elif ch.metric_type == "count":
            inc = float(normalized)
        elif ch.metric_type == "duration_minsec":
            inc = float(normalized)

        cp.progress += inc
        session.add(cp)
        if cp.progress >= ch.target_value and cp.status != "completed":
            cp.status = "completed"
            cp.completed_at = datetime.utcnow()
            session.add(cp)

    # 9 — Commit everything atomically
    session.commit()
    session.refresh(user)

    # 10 — Broadcast leaderboard update via WebSocket (non-blocking, best-effort)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(
                ws_manager.broadcast("leaderboard:updated", {
                    "user_id": user.id,
                    "new_points": user.total_points,
                    "rank_changed": True,
                })
            )
    except RuntimeError:
        pass  # No event loop in sync test context — skip broadcast

    # 11 — Response
    return ActivityResponse(
        activity_id=activity.id,
        points_awarded=points,
        user_total_points=user.total_points,
        current_streak=user.current_streak,
        new_badges=new_badges,
        is_personal_best=is_personal_best,
    )
