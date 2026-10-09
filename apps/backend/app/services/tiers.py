"""
Performance tier system.
Computed from total_points — never stored, never requires personal health data.
Tiers update automatically the moment an activity is logged.
"""

TIER_RANGES: dict[str, tuple] = {
    "elite":      (10001, float("inf")),
    "competitor": (5001,  10000),
    "athlete":    (2001,  5000),
    "active":     (501,   2000),
    "rookie":     (0,     500),
}

TIER_EMOJI: dict[str, str] = {
    "elite":      "🏆",
    "competitor": "🥈",
    "athlete":    "🏃",
    "active":     "⚡",
    "rookie":     "🌱",
}


def get_tier(total_points: int) -> str:
    """Return tier name for a given point total."""
    for tier, (low, high) in TIER_RANGES.items():
        if low <= total_points <= high:
            return tier
    return "rookie"


def get_tier_progress(total_points: int) -> dict:
    """
    Return tier name, emoji, progress percentage, and points to next tier.

    For 'elite' tier progress_pct is always 100.
    """
    tier = get_tier(total_points)
    low, high = TIER_RANGES[tier]

    if tier == "elite":
        return {
            "tier": tier,
            "emoji": TIER_EMOJI[tier],
            "progress_pct": 100,
            "points_to_next": 0,
        }

    progress_pct = int(((total_points - low) / (high - low)) * 100)
    return {
        "tier": tier,
        "emoji": TIER_EMOJI[tier],
        "progress_pct": progress_pct,
        "points_to_next": high - total_points + 1,
    }
