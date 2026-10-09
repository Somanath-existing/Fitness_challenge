"""
Personalised coaching insights using Groq AI.
Cached per user for 1 hour. Falls back to generic tips on API failure.

SECURITY: No user-supplied text in prompts. Aggregate stats only.
"""
from __future__ import annotations
import json
import os
import logging
from datetime import datetime, timedelta
from groq import Groq

from app.services.tiers import get_tier

logger = logging.getLogger(__name__)

_client: Groq | None = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=api_key)
    return _client


# 1-hour cache: { user_id: (generated_at: datetime, insights: list) }
_insights_cache: dict[str, tuple[datetime, list]] = {}

FALLBACK_INSIGHTS = [
    {
        "icon": "🏃",
        "title": "Consistency beats intensity",
        "text": "Logging any activity — even a short walk — every day compounds faster than sporadic big sessions.",
    },
    {
        "icon": "💧",
        "title": "Hydration is free performance",
        "text": "Drink 500ml of water before every workout. Dehydration reduces performance by up to 10%.",
    },
    {
        "icon": "😴",
        "title": "Sleep is your best recovery tool",
        "text": "7–9 hours of sleep boosts muscle repair, motivation, and next-day performance more than any supplement.",
    },
]


import re

async def get_insights(user, recent_activities: list) -> list[dict]:
    """
    Returns 3 personalised coaching insights.
    Cached per user for 1 hour. Falls back to generic tips on Groq failure.
    """
    cache_key = user.id
    cached = _insights_cache.get(cache_key)
    if cached:
        generated_at, data = cached
        if datetime.utcnow() - generated_at < timedelta(hours=1):
            return data

    try:
        return await _generate_insights(user, recent_activities, cache_key)
    except Exception as exc:
        logger.warning("Groq insights error for user %s: %s. Using fallback.", user.id, exc)
        # Note: Do not cache fallback for 1 hour so future requests can retry Groq AI
        return FALLBACK_INSIGHTS


async def _generate_insights(user, activities: list, cache_key: str) -> list[dict]:
    """Generate 3 coaching insights from Groq. Only aggregate stats in the prompt."""
    sport_freq: dict[str, int] = {}
    total_points_7d = 0
    total_points_30d = 0

    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    cutoff_30d = datetime.utcnow() - timedelta(days=30)

    for a in activities:
        sport_freq[a.sport] = sport_freq.get(a.sport, 0) + 1
        if a.logged_at >= cutoff_7d:
            total_points_7d += a.points_awarded
        if a.logged_at >= cutoff_30d:
            total_points_30d += a.points_awarded

    tier = get_tier(user.total_points)
    all_sports = ["running", "walking", "cycling", "gym", "swimming", "steps"]
    neglected = [s for s in all_sports if s not in sport_freq]

    prompt = f"""You are a fitness coach generating personalised insights. Return ONLY valid JSON - no preamble, no markdown fences.

User stats:
- tier: {tier}
- streak: {user.current_streak} days
- total_points: {user.total_points}
- points_last_7_days: {total_points_7d}
- points_last_30_days: {total_points_30d}
- sport_frequency: {sport_freq}
- neglected_sports: {neglected}
- weekly_fitness_goal: {user.fitness_goal}

Generate exactly 3 coaching insights. Each should be specific to this user's data.

Return exactly this JSON:
[
  {{"icon": "one emoji", "title": "max 5 words", "text": "2-3 sentence specific coaching insight"}},
  {{"icon": "one emoji", "title": "max 5 words", "text": "2-3 sentence specific coaching insight"}},
  {{"icon": "one emoji", "title": "max 5 words", "text": "2-3 sentence specific coaching insight"}}
]"""

    client = get_groq_client()
    raw_text = ""
    last_err = None

    # Try fast model first, fallback to reasoning model with high token allowance
    models_to_try = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
    for model_name in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.7,
            )
            raw_text = response.choices[0].message.content or ""
            if raw_text.strip():
                break
        except Exception as e:
            last_err = e
            continue

    if not raw_text.strip() and last_err:
        raise last_err

    cleaned = raw_text.strip()
    if "```" in cleaned:
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()

    # Extract JSON array bounds if extra text is present
    array_match = re.search(r"\[[\s\S]*\]", cleaned)
    if array_match:
        cleaned = array_match.group(0)

    data = json.loads(cleaned)
    if not isinstance(data, list) or len(data) != 3:
        raise ValueError(f"Expected list of 3 insights, got {type(data)} with len {len(data) if isinstance(data, list) else 0}")

    _insights_cache[cache_key] = (datetime.utcnow(), data)
    return data
