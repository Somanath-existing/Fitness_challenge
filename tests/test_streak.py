"""
Streak calculation tests — timezone-aware logic.
"""
import pytest
import sys, os
from datetime import datetime, date
import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.services.streak import compute_streak


def utc(dt_str: str) -> datetime:
    """Helper: parse naive UTC string to aware UTC datetime."""
    return pytz.utc.localize(datetime.fromisoformat(dt_str))


class TestComputeStreak:
    def test_first_activity_ever(self):
        streak, last_date = compute_streak(
            last_active_date=None,
            current_streak=0,
            logged_at=utc("2026-10-08T10:00:00"),
            user_timezone="UTC",
        )
        assert streak == 1
        assert last_date == date(2026, 10, 8)

    def test_consecutive_day_increments(self):
        streak, last_date = compute_streak(
            last_active_date=date(2026, 10, 7),
            current_streak=3,
            logged_at=utc("2026-10-08T10:00:00"),
            user_timezone="UTC",
        )
        assert streak == 4
        assert last_date == date(2026, 10, 8)

    def test_same_day_no_change(self):
        """Logging twice on the same day doesn't increment streak."""
        streak, last_date = compute_streak(
            last_active_date=date(2026, 10, 8),
            current_streak=3,
            logged_at=utc("2026-10-08T15:00:00"),
            user_timezone="UTC",
        )
        assert streak == 3
        assert last_date == date(2026, 10, 8)

    def test_missed_day_resets_to_1(self):
        streak, last_date = compute_streak(
            last_active_date=date(2026, 10, 5),
            current_streak=7,
            logged_at=utc("2026-10-08T10:00:00"),
            user_timezone="UTC",
        )
        assert streak == 1
        assert last_date == date(2026, 10, 8)

    def test_timezone_kolkata_crosses_midnight(self):
        """
        Activity at 2026-10-08 23:30 IST = 2026-10-08 18:00 UTC.
        In IST it's still Oct 8; in UTC it would look like Oct 8 too — but
        the key is the LOCAL date is used for streak logic.
        """
        # IST = UTC+5:30
        # 2026-10-08 23:30 IST = 2026-10-08 18:00:00 UTC
        logged_utc = utc("2026-10-08T18:00:00")
        streak, last_date = compute_streak(
            last_active_date=date(2026, 10, 7),
            current_streak=5,
            logged_at=logged_utc,
            user_timezone="Asia/Kolkata",
        )
        # Local date in IST is Oct 8, which is day after Oct 7 → consecutive
        assert streak == 6
        assert last_date == date(2026, 10, 8)

    def test_timezone_midnight_boundary(self):
        """
        00:01 UTC on Oct 9 = 05:31 IST on Oct 9.
        If last active date was Oct 8 (local), this is consecutive.
        """
        logged_utc = utc("2026-10-08T18:31:00")  # 00:01 IST Oct 9
        streak, last_date = compute_streak(
            last_active_date=date(2026, 10, 8),
            current_streak=10,
            logged_at=logged_utc,
            user_timezone="Asia/Kolkata",
        )
        # Local IST date is Oct 9, last was Oct 8 → consecutive
        assert streak == 11

    def test_naive_datetime_treated_as_utc(self):
        """Naive datetimes (no tzinfo) should work without crashing."""
        naive_dt = datetime(2026, 10, 8, 10, 0, 0)  # no tzinfo
        streak, _ = compute_streak(
            last_active_date=date(2026, 10, 7),
            current_streak=2,
            logged_at=naive_dt,
            user_timezone="UTC",
        )
        assert streak == 3
