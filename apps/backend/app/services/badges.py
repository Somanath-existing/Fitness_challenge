"""
Badge unlock evaluation.
Called on every activity insert with the updated user + session.
Returns list of newly unlocked badge IDs (empty if none).
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from sqlmodel import Session, select, func

from app.models.activity import Activity
from app.models.user import User


BADGE_DEFINITIONS = {
    "first_step":       "First Step — log your first activity",
    "7day_warrior":     "7-Day Warrior — 7-day streak",
    "30day_legend":     "30-Day Legend — 30-day streak",
    "marathon_runner":  "Marathon Runner — 500km total running",
    "iron_human":       "Iron Human — all 6 sports in one week",
    "point_machine":    "Point Machine — 1000 points in a single day",
    "challenge_victor": "Challenge Victor — complete 5 challenges",
}

ALL_SPORTS = {"running", "walking", "cycling", "gym", "swimming", "steps"}


def evaluate_badges(user: User, activity: Activity, session: Session) -> list[str]:
    """
    Evaluate which badges should be unlocked after this activity.
    Modifies user.badges in-place.
    Caller must commit the session.

    Returns:
        List of newly unlocked badge IDs (empty list if none).
    """
    current_badges: list[str] = json.loads(user.badges or "[]")
    new_badges: list[str] = []

    def unlock(badge_id: str) -> None:
        if badge_id not in current_badges:
            new_badges.append(badge_id)
            current_badges.append(badge_id)

    # ── First activity ever ───────────────────────────────────────────────────
    activity_count = session.exec(
        select(func.count(Activity.id)).where(Activity.user_id == user.id)
    ).one()
    if activity_count == 1:
        unlock("first_step")

    # ── Streak badges ─────────────────────────────────────────────────────────
    if user.current_streak >= 30:
        unlock("30day_legend")
    if user.current_streak >= 7:
        unlock("7day_warrior")

    # ── Marathon runner — 500km total running ─────────────────────────────────
    running_km = session.exec(
        select(func.sum(Activity.normalized_value))
        .where(Activity.user_id == user.id, Activity.sport == "running")
    ).one()
    if running_km and running_km >= 500:
        unlock("marathon_runner")

    # ── Iron Human — all 6 sports in last 7 days ─────────────────────────────
    week_ago = datetime.utcnow() - timedelta(days=7)
    sports_this_week = session.exec(
        select(Activity.sport)
        .where(Activity.user_id == user.id, Activity.logged_at >= week_ago)
        .distinct()
    ).all()
    if ALL_SPORTS.issubset(set(sports_this_week)):
        unlock("iron_human")

    # ── Point Machine — 1000 points in a single day ──────────────────────────
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_points = session.exec(
        select(func.sum(Activity.points_awarded))
        .where(
            Activity.user_id == user.id,
            Activity.logged_at >= today_start,
        )
    ).one()
    if daily_points and daily_points >= 1000:
        unlock("point_machine")

    # Persist updated badge list
    if new_badges:
        user.badges = json.dumps(current_badges)

    return new_badges
