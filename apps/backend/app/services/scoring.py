"""
Scoring engine — pure functions only.
No database imports. Fully testable in isolation.

Floor rules per sport:
  distance sports:  floor(km × rate)
  duration sports:  floor(seconds/60) first, then × rate
  steps:            floor(steps/100)×100 first, then ÷100 × rate
"""
from __future__ import annotations
import math
from enum import Enum


class SportType(str, Enum):
    running = "running"
    walking = "walking"
    cycling = "cycling"
    gym = "gym"
    swimming = "swimming"
    steps = "steps"


# Points per unit
RATES: dict[SportType, int] = {
    SportType.running: 100,
    SportType.walking: 50,
    SportType.cycling: 25,
    SportType.swimming: 15,
    SportType.gym: 5,
    SportType.steps: 1,
}

# Each sport accepts exactly one metric type
SPORT_METRIC_MAP: dict[SportType, str] = {
    SportType.running: "distance_km",
    SportType.walking: "distance_km",
    SportType.cycling: "distance_km",
    SportType.gym: "duration_minsec",
    SportType.swimming: "duration_minsec",
    SportType.steps: "count",
}

# Reasonable upper bounds to prevent database int overflow
MAX_VALUES: dict[SportType, float] = {
    SportType.running: 1000.0,
    SportType.walking: 1000.0,
    SportType.cycling: 1000.0,
    SportType.gym: 999 * 60 + 59,    # 999:59 in seconds
    SportType.swimming: 999 * 60 + 59,
    SportType.steps: 200_000,
}


def parse_duration(raw: str) -> int:
    """
    'MM:SS' string → whole minutes (floor division).

    Examples:
        '1:55' → 1     (115 seconds → 1 minute)
        '0:59' → 0
        '45:30' → 45
        '0:00' → 0

    Raises ValueError on bad format.
    """
    raw = str(raw).strip()
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid duration format '{raw}'. Expected MM:SS (e.g. '45:30')"
        )
    try:
        mins = int(parts[0])
        secs = int(parts[1])
    except ValueError:
        raise ValueError(f"Duration parts must be integers, got '{raw}'")

    if mins < 0:
        raise ValueError("Minutes cannot be negative")
    if not (0 <= secs <= 59):
        raise ValueError(f"Seconds must be 0–59, got {secs}")

    total_seconds = mins * 60 + secs
    return math.floor(total_seconds / 60)


def calculate_points(sport: SportType, value: object) -> dict:
    """
    Calculate points for a given sport + raw value.

    Returns:
        {"points": int, "normalized": float, "raw": str}

    Raises ValueError on invalid input.
    """
    rate = RATES[sport]

    # ── Duration sports (gym, swimming) ──────────────────────────────────────
    if sport in (SportType.gym, SportType.swimming):
        minutes = parse_duration(str(value))
        # Check upper bound (999:59)
        if minutes * 60 > MAX_VALUES[sport]:
            raise ValueError(f"Duration exceeds maximum allowed value")
        points = minutes * rate
        return {"points": points, "normalized": float(minutes), "raw": str(value)}

    # ── Steps ─────────────────────────────────────────────────────────────────
    if sport == SportType.steps:
        try:
            steps = int(float(str(value)))
        except (ValueError, TypeError):
            raise ValueError(f"Steps must be a whole number, got '{value}'")
        if steps < 0:
            raise ValueError("Steps cannot be negative")
        if steps > MAX_VALUES[sport]:
            raise ValueError(f"Steps exceeds maximum allowed value ({MAX_VALUES[sport]})")
        # Floor to nearest 100 first
        floored = math.floor(steps / 100) * 100   # 399 → 300, 99 → 0
        points = (floored // 100) * rate           # rate=1, so points = floored/100
        return {"points": points, "normalized": float(floored), "raw": str(value)}

    # ── Distance sports (running, walking, cycling) ───────────────────────────
    try:
        km = float(str(value))
    except (ValueError, TypeError):
        raise ValueError(f"Distance must be a number, got '{value}'")
    if km < 0:
        raise ValueError(f"Distance cannot be negative")
    if km > MAX_VALUES[sport]:
        raise ValueError(f"Distance exceeds maximum allowed value ({MAX_VALUES[sport]}km)")
    points = math.floor(km * rate)
    return {"points": points, "normalized": km, "raw": str(value)}


def validate_sport_metric(sport: SportType, metric_type: str) -> bool:
    """True if metric_type is the correct type for this sport."""
    return SPORT_METRIC_MAP.get(sport) == metric_type
