import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "backend"))

from app.services.challenge import validate_daily_challenge


@pytest.mark.parametrize(
    ("sport", "metric_type", "target"),
    [
        ("running", "distance_km", 5),
        ("walking", "distance_km", 2.5),
        ("cycling", "distance_km", 15),
        ("gym", "duration_minsec", "30:00"),
        ("swimming", "duration_minsec", 20),
        ("steps", "count", 10000),
    ],
)
def test_daily_challenge_accepts_metric_matching_sport(sport, metric_type, target):
    challenge = {
        "sport": sport,
        "metric": {"type": metric_type, "target": target},
    }

    assert validate_daily_challenge(challenge) is challenge


def test_daily_challenge_rejects_running_duration():
    challenge = {
        "sport": "running",
        "metric": {"type": "duration_minsec", "target": 30},
    }

    with pytest.raises(ValueError, match="requires metric"):
        validate_daily_challenge(challenge)


def test_daily_challenge_rejects_fractional_step_target():
    challenge = {
        "sport": "steps",
        "metric": {"type": "count", "target": 1000.5},
    }

    with pytest.raises(ValueError, match="whole number"):
        validate_daily_challenge(challenge)


def test_daily_challenge_rejects_duration_wording_for_distance_target():
    challenge = {
        "sport": "running",
        "title": "30-minute run",
        "description": "Run for 30 minutes.",
        "metric": {"type": "distance_km", "target": 5},
    }

    with pytest.raises(ValueError, match="duration units"):
        validate_daily_challenge(challenge)
