"""
Scoring engine tests — every edge case from the spec.
Run: cd apps/backend && python -m pytest ../../tests/ -v
"""
import pytest
import sys
import os

# Make sure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.services.scoring import (
    calculate_points, parse_duration, validate_sport_metric, SportType
)


# ── parse_duration ────────────────────────────────────────────────────────────

class TestParseDuration:
    def test_one_min_55_sec(self):
        assert parse_duration("1:55") == 1   # 115s → 1 minute (floor)

    def test_exact_minutes(self):
        assert parse_duration("45:00") == 45

    def test_zero_duration(self):
        assert parse_duration("0:00") == 0

    def test_59_seconds_floors_to_zero(self):
        assert parse_duration("0:59") == 0

    def test_45_30(self):
        assert parse_duration("45:30") == 45  # 2730s → 45 minutes (floor)

    def test_invalid_seconds_60(self):
        with pytest.raises(ValueError, match="Seconds"):
            parse_duration("1:60")

    def test_invalid_seconds_99(self):
        with pytest.raises(ValueError):
            parse_duration("1:99")

    def test_invalid_format_no_colon(self):
        with pytest.raises(ValueError, match="MM:SS"):
            parse_duration("45")

    def test_invalid_format_letters(self):
        with pytest.raises(ValueError):
            parse_duration("not-a-time")

    def test_invalid_format_extra_colon(self):
        with pytest.raises(ValueError):
            parse_duration("1:30:00")

    def test_negative_minutes(self):
        with pytest.raises(ValueError):
            parse_duration("-1:30")

    def test_large_duration(self):
        assert parse_duration("999:59") == 999  # max allowed


# ── Distance sports ───────────────────────────────────────────────────────────

class TestRunning:
    def test_exact_km(self):
        r = calculate_points(SportType.running, 5.0)
        assert r["points"] == 500

    def test_floor_applied(self):
        # 5.5 * 100 = 550.0 → floor = 550
        r = calculate_points(SportType.running, 5.5)
        assert r["points"] == 550

    def test_fractional_floor(self):
        # 1.55 * 100 = 155.0 → floor = 155
        r = calculate_points(SportType.running, 1.55)
        assert r["points"] == 155

    def test_just_below_integer(self):
        # 4.999 * 100 = 499.9 → floor = 499
        r = calculate_points(SportType.running, 4.999)
        assert r["points"] == 499

    def test_zero_distance(self):
        r = calculate_points(SportType.running, 0)
        assert r["points"] == 0

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="negative"):
            calculate_points(SportType.running, -1)

    def test_string_float_accepted(self):
        r = calculate_points(SportType.running, "5.5")
        assert r["points"] == 550

    def test_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="maximum"):
            calculate_points(SportType.running, 1001)

    def test_normalized_value(self):
        r = calculate_points(SportType.running, 5.5)
        assert r["normalized"] == 5.5


class TestWalking:
    def test_rate_50(self):
        r = calculate_points(SportType.walking, 2.0)
        assert r["points"] == 100

    def test_floor(self):
        # 1.55 * 50 = 77.5 → floor = 77
        r = calculate_points(SportType.walking, 1.55)
        assert r["points"] == 77

    def test_zero(self):
        assert calculate_points(SportType.walking, 0)["points"] == 0


class TestCycling:
    def test_rate_25(self):
        r = calculate_points(SportType.cycling, 4.0)
        assert r["points"] == 100

    def test_floor(self):
        # 3.7 * 25 = 92.5 → floor = 92
        r = calculate_points(SportType.cycling, 3.7)
        assert r["points"] == 92

    def test_zero(self):
        assert calculate_points(SportType.cycling, 0)["points"] == 0


# ── Duration sports ───────────────────────────────────────────────────────────

class TestSwimming:
    def test_1min_55sec_floors_to_1min(self):
        # 1:55 → 1 minute → 1 * 15 = 15 pts
        r = calculate_points(SportType.swimming, "1:55")
        assert r["points"] == 15

    def test_30_minutes(self):
        r = calculate_points(SportType.swimming, "30:00")
        assert r["points"] == 450

    def test_zero_duration(self):
        r = calculate_points(SportType.swimming, "0:00")
        assert r["points"] == 0

    def test_invalid_seconds_raises(self):
        with pytest.raises(ValueError):
            calculate_points(SportType.swimming, "1:60")

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            calculate_points(SportType.swimming, "badformat")


class TestGym:
    def test_45_30_floors_to_45(self):
        # 45:30 → 45 min → 45 * 5 = 225 pts
        r = calculate_points(SportType.gym, "45:30")
        assert r["points"] == 225

    def test_exact_45_minutes(self):
        r = calculate_points(SportType.gym, "45:00")
        assert r["points"] == 225

    def test_zero_duration(self):
        r = calculate_points(SportType.gym, "0:00")
        assert r["points"] == 0

    def test_1_hour(self):
        r = calculate_points(SportType.gym, "60:00")
        assert r["points"] == 300

    def test_normalized_is_minutes(self):
        r = calculate_points(SportType.gym, "45:30")
        assert r["normalized"] == 45.0


# ── Steps ─────────────────────────────────────────────────────────────────────

class TestSteps:
    def test_399_floors_to_300(self):
        # 399 → floor(399/100)*100 = 300 → 300/100 * 1 = 3 pts
        r = calculate_points(SportType.steps, 399)
        assert r["points"] == 3

    def test_100_exact(self):
        r = calculate_points(SportType.steps, 100)
        assert r["points"] == 1

    def test_99_floors_to_zero(self):
        r = calculate_points(SportType.steps, 99)
        assert r["points"] == 0

    def test_zero_steps(self):
        r = calculate_points(SportType.steps, 0)
        assert r["points"] == 0

    def test_1000_steps(self):
        r = calculate_points(SportType.steps, 1000)
        assert r["points"] == 10

    def test_10000_steps(self):
        r = calculate_points(SportType.steps, 10000)
        assert r["points"] == 100

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="negative"):
            calculate_points(SportType.steps, -1)

    def test_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="maximum"):
            calculate_points(SportType.steps, 200001)

    def test_float_truncated(self):
        # 150.9 → int → 150 → floor to 100 → 1 pt
        r = calculate_points(SportType.steps, 150.9)
        assert r["points"] == 1

    def test_normalized_is_floored(self):
        r = calculate_points(SportType.steps, 399)
        assert r["normalized"] == 300.0


# ── validate_sport_metric ─────────────────────────────────────────────────────

class TestSportMetricValidation:
    def test_running_distance_ok(self):
        assert validate_sport_metric(SportType.running, "distance_km") is True

    def test_running_count_fail(self):
        assert validate_sport_metric(SportType.running, "count") is False

    def test_gym_duration_ok(self):
        assert validate_sport_metric(SportType.gym, "duration_minsec") is True

    def test_gym_distance_fail(self):
        assert validate_sport_metric(SportType.gym, "distance_km") is False

    def test_steps_count_ok(self):
        assert validate_sport_metric(SportType.steps, "count") is True

    def test_steps_distance_fail(self):
        assert validate_sport_metric(SportType.steps, "distance_km") is False

    def test_swimming_duration_ok(self):
        assert validate_sport_metric(SportType.swimming, "duration_minsec") is True

    def test_cycling_distance_ok(self):
        assert validate_sport_metric(SportType.cycling, "distance_km") is True

    def test_walking_distance_ok(self):
        assert validate_sport_metric(SportType.walking, "distance_km") is True
