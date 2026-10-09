"""
Streak calculation respecting user timezone.
A 'day' is defined in the user's local timezone — critical for fairness.
A user in Asia/Kolkata logging at 11:30 PM IST on day N must count as day N
(not day N+1 in UTC which would be the case without timezone awareness).
"""
from datetime import date, datetime, timedelta
from typing import Optional
import pytz


def compute_streak(
    last_active_date: Optional[date],
    current_streak: int,
    logged_at: datetime,
    user_timezone: str,
) -> tuple[int, date]:
    """
    Given a new activity timestamp, compute the updated streak and new last_active_date.

    Returns:
        (new_streak: int, new_last_active_date: date)

    Logic:
        - Convert logged_at to user's local timezone
        - If user has never logged before → streak = 1
        - If today == last_active_date → same day, streak unchanged (no double-count)
        - If today == last_active_date + 1 day → consecutive, streak + 1
        - Otherwise → streak reset to 1
    """
    tz = pytz.timezone(user_timezone)

    # Convert the UTC activity timestamp to the user's local date
    if logged_at.tzinfo is None:
        logged_at = pytz.utc.localize(logged_at)
    local_dt = logged_at.astimezone(tz)
    today_local = local_dt.date()

    if last_active_date is None:
        # First ever activity
        return 1, today_local

    if today_local == last_active_date:
        # Already logged today — don't increment streak, don't change date
        return current_streak, last_active_date

    if today_local == last_active_date + timedelta(days=1):
        # Consecutive day
        return current_streak + 1, today_local

    # Streak broken
    return 1, today_local
