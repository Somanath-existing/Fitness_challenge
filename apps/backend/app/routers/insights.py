"""
AI coaching insights router.
GET /api/users/{user_id}/insights — 3 personalised insights from Groq.

Security:
- Requires authentication.
- Ownership-enforced: users can only fetch their own insights.
- Strictly rate-limited: 5 requests/hour/IP to protect against Groq API abuse.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User
from app.models.activity import Activity
from app.dependencies import get_current_user, require_self, rate_limit
from app.services.insights import get_insights

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["insights"])

# Strict rate limit — each call hits the Groq API (cost + abuse protection)
_insights_rate_limit = rate_limit(max_calls=5, window_seconds=3600)


@router.get(
    "/{user_id}/insights",
    dependencies=[Depends(_insights_rate_limit)],
)
async def get_coaching_insights(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Returns 3 AI-generated coaching insights for the authenticated user.
    SECURITY: 403 if user requests insights for a different user (IDOR).
    Falls back to generic tips if Groq is unavailable.
    """
    require_self(user_id, current_user)

    target_id = current_user.id if user_id == "me" else user_id
    user = current_user if user_id == "me" else session.get(User, target_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    cutoff = datetime.utcnow() - timedelta(days=30)
    recent_activities = session.exec(
        select(Activity)
        .where(Activity.user_id == user.id, Activity.logged_at >= cutoff)
        .order_by(Activity.logged_at.desc())  # type: ignore[union-attr]
    ).all()

    insights = await get_insights(user, recent_activities)
    return {"insights": insights, "cached_at": datetime.utcnow().isoformat()}
