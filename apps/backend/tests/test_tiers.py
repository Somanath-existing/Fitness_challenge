"""
Performance tier tests.
"""
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.services.tiers import get_tier, get_tier_progress


class TestGetTier:
    def test_zero_is_rookie(self):
        assert get_tier(0) == "rookie"

    def test_500_is_rookie(self):
        assert get_tier(500) == "rookie"

    def test_501_is_active(self):
        assert get_tier(501) == "active"

    def test_2000_is_active(self):
        assert get_tier(2000) == "active"

    def test_2001_is_athlete(self):
        assert get_tier(2001) == "athlete"

    def test_5000_is_athlete(self):
        assert get_tier(5000) == "athlete"

    def test_5001_is_competitor(self):
        assert get_tier(5001) == "competitor"

    def test_10000_is_competitor(self):
        assert get_tier(10000) == "competitor"

    def test_10001_is_elite(self):
        assert get_tier(10001) == "elite"

    def test_large_points_is_elite(self):
        assert get_tier(999999) == "elite"

    def test_exact_boundaries_inclusive(self):
        """Every boundary value maps to the correct tier."""
        boundaries = {
            0: "rookie", 500: "rookie",
            501: "active", 2000: "active",
            2001: "athlete", 5000: "athlete",
            5001: "competitor", 10000: "competitor",
            10001: "elite",
        }
        for pts, expected in boundaries.items():
            assert get_tier(pts) == expected, f"Failed at {pts} pts"


class TestGetTierProgress:
    def test_rookie_has_progress(self):
        result = get_tier_progress(250)
        assert result["tier"] == "rookie"
        assert 0 <= result["progress_pct"] <= 100
        assert result["points_to_next"] > 0

    def test_elite_is_100_pct(self):
        result = get_tier_progress(15000)
        assert result["tier"] == "elite"
        assert result["progress_pct"] == 100
        assert result["points_to_next"] == 0

    def test_midpoint_athlete(self):
        # Midpoint of athlete range: 2001–5000, midpoint ~3500
        result = get_tier_progress(3500)
        assert result["tier"] == "athlete"
        assert 40 <= result["progress_pct"] <= 60

    def test_all_tiers_have_emoji(self):
        for pts in [0, 1000, 3000, 7000, 15000]:
            result = get_tier_progress(pts)
            assert "emoji" in result
            assert result["emoji"]  # non-empty
