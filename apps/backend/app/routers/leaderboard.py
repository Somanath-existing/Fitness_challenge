"""
Leaderboard router.
GET /api/leaderboard — global and friends-scoped rankings.

Rank is computed server-side (ORDER BY total_points DESC).
The descending index on total_points makes this O(log N) for large tables.
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlmodel import Session, select
import json

from app.database import get_session
from app.models.user import User
from app.models.friendship import Friendship
from app.schemas import LeaderboardResponse, LeaderboardEntry
from typing import Optional
from app.dependencies import get_optional_current_user
from app.services.tiers import get_tier

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=LeaderboardResponse)
def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tier: str | None = Query(default=None),
    scope: str = Query(default="global", pattern=r"^(global|friends)$"),
    user_id: str | None = Query(default=None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    """
    Returns ranked list of users.

    scope=global  — everyone, sorted by total_points DESC
    scope=friends — only accepted friends of current user or user_id
    tier          — optional filter by tier name
    """
    if scope == "friends":
        effective_user_id = (current_user.id if current_user else None) or user_id
        if not effective_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "MISSING_PARAM",
                    "message": "Authentication or user_id is required for scope=friends",
                },
            )
        user_id = effective_user_id

    # Build base query
    query = select(User).order_by(User.total_points.desc())  # type: ignore[union-attr]

    # Apply scope filter
    if scope == "friends" and user_id:
        # Get accepted friend IDs
        friend_rows = session.exec(
            select(Friendship).where(
                Friendship.status == "accepted",
                (Friendship.requester_id == user_id) | (Friendship.addressee_id == user_id),
            )
        ).all()
        friend_ids = set()
        for f in friend_rows:
            friend_ids.add(f.requester_id if f.addressee_id == user_id else f.addressee_id)
        friend_ids.add(user_id)  # Include self
        query = query.where(User.id.in_(friend_ids))  # type: ignore[union-attr]

    # Count total before pagination
    all_users = session.exec(query).all()
    total = len(all_users)

    # Apply tier filter after fetch (computed field)
    if tier:
        all_users = [u for u in all_users if get_tier(u.total_points) == tier]
        total = len(all_users)

    # Paginate
    paginated = all_users[offset : offset + limit]

    # Build response with global rank
    entries = []
    for global_idx, user in enumerate(all_users):
        if user not in paginated:
            continue
        rank = global_idx + 1  # 1-based rank within full sorted list

        entries.append(
            LeaderboardEntry(
                rank=rank,
                rank_delta=0,  # TODO: implement daily snapshot delta
                user_id=user.id,
                first_name=user.first_name,
                username=user.username,
                total_points=user.total_points,
                tier=get_tier(user.total_points),
                current_streak=user.current_streak,
                badges=json.loads(user.badges or "[]"),
            )
        )

    # Sort entries by rank for output
    entries.sort(key=lambda e: e.rank)

    return LeaderboardResponse(
        data=entries,
        total=total,
        generated_at=datetime.utcnow(),
    )
