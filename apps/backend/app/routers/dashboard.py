"""
Dashboard router.
GET /api/users/{user_id}/dashboard — full chart data for the authenticated user.
GET /api/users/{user_id}/profile  — public profile data visible to accepted friends.

Security:
- Requires authentication (JWT).
- /dashboard enforces ownership: only the authenticated user can access their own dashboard.
- /profile enforces friendship: only accepted friends of the target can view their profile.
- Rate-limited: 60 req/hr per IP.
"""
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import json

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.user import User
from app.models.activity import Activity
from app.models.friendship import Friendship
from app.schemas import (
    DashboardResponse, SportBreakdownItem,
    WeeklyTrendItem, HeatmapItem, GoalProgress,
)
from app.services.tiers import get_tier_progress
from app.dependencies import get_current_user, require_self, rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["dashboard"])

_dashboard_rate_limit = rate_limit(max_calls=60, window_seconds=3600)


def _build_dashboard_payload(
    user: User, user_id: str, session: Session
) -> DashboardResponse:
    """Shared helper: build the DashboardResponse for any given user."""
    rank_result = session.exec(
        select(func.count(User.id)).where(User.total_points > user.total_points)
    ).one()
    rank = (rank_result or 0) + 1

    activities = session.exec(
        select(Activity)
        .where(Activity.user_id == user.id)
        .order_by(Activity.logged_at.desc())  # type: ignore[union-attr]
    ).all()

    sport_totals: dict[str, int] = defaultdict(int)
    for a in activities:
        sport_totals[a.sport] += a.points_awarded

    total_all = sum(sport_totals.values()) or 1
    sport_breakdown = [
        SportBreakdownItem(
            sport=sport,
            total_points=pts,
            percentage=round((pts / total_all) * 100, 1),
        )
        for sport, pts in sorted(sport_totals.items(), key=lambda x: -x[1])
    ]

    weekly: dict[str, int] = defaultdict(int)
    cutoff_8w = datetime.utcnow() - timedelta(weeks=8)
    for a in activities:
        if a.logged_at >= cutoff_8w:
            iso_week = a.logged_at.strftime("%G-W%V")
            weekly[iso_week] += a.points_awarded

    weekly_trend = [
        WeeklyTrendItem(week=week, points=pts)
        for week, pts in sorted(weekly.items())
    ]

    daily: dict[str, int] = defaultdict(int)
    cutoff_1y = datetime.utcnow() - timedelta(days=365)
    for a in activities:
        if a.logged_at >= cutoff_1y:
            day_str = a.logged_at.strftime("%Y-%m-%d")
            daily[day_str] += a.points_awarded

    heatmap = [
        HeatmapItem(date=day, points=pts)
        for day, pts in sorted(daily.items())
    ]

    recent = [
        {
            "id": a.id,
            "sport": a.sport,
            "metric_type": a.metric_type,
            "raw_value": a.raw_value,
            "points_awarded": a.points_awarded,
            "title": a.title,
            "logged_at": a.logged_at.isoformat(),
            "source": a.source,
        }
        for a in activities[:10]
    ]

    goal_progress = None
    if user.fitness_goal:
        week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_points = session.exec(
            select(func.sum(Activity.points_awarded))
            .where(Activity.user_id == user.id, Activity.logged_at >= week_start)
        ).one() or 0
        goal_progress = GoalProgress(
            target=user.fitness_goal,
            achieved=week_points,
            percentage=round(min((week_points / user.fitness_goal) * 100, 100), 1),
        )

    tier_data = get_tier_progress(user.total_points)

    return DashboardResponse(
        user={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "total_points": user.total_points,
            "rank": rank,
            "tier": tier_data["tier"],
            "tier_emoji": tier_data["emoji"],
            "tier_progress_pct": tier_data["progress_pct"],
            "points_to_next_tier": tier_data.get("points_to_next", 0),
            "streak": user.current_streak,
            "badges": json.loads(user.badges or "[]"),
        },
        sport_breakdown=sport_breakdown,
        weekly_trend=weekly_trend,
        heatmap=heatmap,
        recent_activities=recent,
        goal_progress=goal_progress,
    )


@router.get(
    "/{user_id}/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(_dashboard_rate_limit)],
)
def get_dashboard(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Fetch private dashboard data for user_id.
    SECURITY: Raises 403 if authenticated user_id != requested user_id (IDOR protection).
    Use /profile instead to view a friend's public profile.
    """
    require_self(user_id, current_user)

    target_id = current_user.id if user_id == "me" else user_id
    user = current_user if user_id == "me" else session.get(User, target_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "USER_NOT_FOUND"},
        )

    return _build_dashboard_payload(user, user_id, session)


@router.get(
    "/{user_id}/profile",
    response_model=DashboardResponse,
    dependencies=[Depends(_dashboard_rate_limit)],
)
def get_friend_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Fetch public profile/dashboard data for a friend.
    SECURITY:
    - The requester must be authenticated.
    - If requesting own profile, returns it directly (same as /dashboard).
    - If requesting another user's profile, validates an accepted friendship exists.
    - Raises 403 if no accepted friendship found (prevents enumeration of profiles).
    """
    # Own profile: same as dashboard
    if user_id == "me" or user_id == current_user.id:
        return _build_dashboard_payload(current_user, current_user.id, session)

    # Must be an accepted friend
    friendship = session.exec(
        select(Friendship).where(
            Friendship.status == "accepted",
            (
                (Friendship.requester_id == current_user.id) & (Friendship.addressee_id == user_id)
            ) | (
                (Friendship.requester_id == user_id) & (Friendship.addressee_id == current_user.id)
            ),
        )
    ).first()

    if not friendship:
        logger.warning(
            "FRIEND_PROFILE_FORBIDDEN viewer=%s target=%s",
            current_user.id, user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "NOT_FRIENDS", "message": "You must be friends to view this profile."},
        )

    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "USER_NOT_FOUND"},
        )

    return _build_dashboard_payload(target_user, user_id, session)
