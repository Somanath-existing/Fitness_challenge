"""
Personalised coaching insights using Groq AI.
Cached per user for 1 hour (5 min on fallback). Falls back to generic tips on API failure.

SECURITY: No user-supplied text in prompts. Aggregate stats only.
"""
from __future__ import annotations
import json
import os
import logging
import re
from datetime import datetime, timedelta
from groq import Groq

from app.services.tiers import get_tier

logger = logging.getLogger(__name__)

_client: Groq | None = None

GROQ_MODELS = [
    "openai/gpt-oss-120b",  # 1st choice: Best quality & domain reasoning
    "qwen/qwen3.8-27b",     # 2nd choice: High speed & solid JSON output
    "openai/gpt-oss-20b",   # 3rd choice: Ultra-fast fallback
]

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


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=api_key)
    return _client


def _build_stats(user, activities: list) -> dict:
    """
    Derive aggregate stats from activities.
    Returns a plain dict — no user text, safe to interpolate into prompts.
    """
    sport_freq: dict[str, int] = {}
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    cutoff_30d = datetime.utcnow() - timedelta(days=30)

    total_points_7d = 0
    total_points_30d = 0
    # 4 weekly buckets: index 0 = current week, 1/2/3 = previous weeks
    weekly_buckets = [0, 0, 0, 0]

    for a in activities:
        sport_freq[a.sport] = sport_freq.get(a.sport, 0) + 1

        days_ago = (datetime.utcnow() - a.logged_at).days
        bucket = max(0, min(days_ago // 7, 3))  # guard against clock-skew giving days_ago=-1
        weekly_buckets[bucket] += a.points_awarded

        if a.logged_at >= cutoff_7d:
            total_points_7d += a.points_awarded
        if a.logged_at >= cutoff_30d:
            total_points_30d += a.points_awarded

    # 3-week baseline (weeks 1-3, excluding the current week)
    avg_weekly_points = sum(weekly_buckets[1:]) // 3 if any(weekly_buckets[1:]) else 0
    delta = total_points_7d - avg_weekly_points
    if avg_weekly_points == 0:
        weekly_trend = f"first active week (+{total_points_7d} pts)"
    else:
        direction = "up" if delta >= 0 else "down"
        pct = abs(round((delta / avg_weekly_points) * 100))
        weekly_trend = f"{direction} {pct}% vs your recent average"

    all_sports = ["running", "walking", "cycling", "gym", "swimming", "steps"]
    neglected = [s for s in all_sports if s not in sport_freq]

    tier = get_tier(user.total_points)

    # Human-readable sport summary — no raw dict braces in the prompt
    sport_summary = (
        ", ".join(
            f"{s}: {c} session{'s' if c != 1 else ''}"
            for s, c in sorted(sport_freq.items(), key=lambda x: -x[1])
        )
        if sport_freq
        else "none yet"
    )
    neglected_str = ", ".join(neglected) if neglected else "none"

    return {
        "tier": tier,
        "streak": user.current_streak,
        "total_points": user.total_points,
        "points_this_week": total_points_7d,
        "points_last_30d": total_points_30d,
        "avg_weekly_points_last_3_weeks": avg_weekly_points,
        "weekly_trend": weekly_trend,
        "sport_summary": sport_summary,
        "neglected_sports": neglected_str,
        "weekly_fitness_goal": user.fitness_goal or "general health & fitness",
    }


def _build_prompt(stats: dict) -> str:
    return f"""You are a fitness coach generating personalised insights. Return ONLY valid JSON — no preamble, no markdown fences.

User stats:
- tier: {stats['tier']}
- streak: {stats['streak']} days
- total_points: {stats['total_points']}
- points_this_week: {stats['points_this_week']}
- avg_weekly_points_last_3_weeks: {stats['avg_weekly_points_last_3_weeks']}
- weekly_trend: {stats['weekly_trend']}
- points_last_30_days: {stats['points_last_30d']}
- sports_logged: {stats['sport_summary']}
- neglected_sports: {stats['neglected_sports']}
- weekly_fitness_goal: {stats['weekly_fitness_goal']}

Rules:
1. Every insight MUST reference at least one specific number from the stats above.
2. Generic advice ("stay consistent", "drink water") is banned unless it directly references the user's numbers.
3. If weekly_trend contains "down", at least one insight must address it with a concrete action.
4. If neglected_sports is not "none", one insight should encourage trying one of them.

Generate exactly 3 coaching insights specific to this user's data.

Return exactly this JSON:
[
  {{"icon": "one emoji", "title": "max 5 words", "text": "2-3 sentence specific coaching insight"}},
  {{"icon": "one emoji", "title": "max 5 words", "text": "2-3 sentence specific coaching insight"}},
  {{"icon": "one emoji", "title": "max 5 words", "text": "2-3 sentence specific coaching insight"}}
]"""


def _parse_and_validate(raw_text: str) -> list[dict]:
    """
    Strip markdown fences, extract the JSON array, parse it, and validate shape.
    Raises ValueError or json.JSONDecodeError on bad output.
    """
    cleaned = raw_text.strip()

    # Strip markdown code fences
    if "```" in cleaned:
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()

    # Extract JSON array even if the model prepended explanation text
    array_match = re.search(r"\[[\s\S]*\]", cleaned)
    if array_match:
        cleaned = array_match.group(0)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(
            f"Failed to parse Groq response as JSON: {exc.msg}",
            exc.doc,
            exc.pos,
        ) from exc

    if not isinstance(data, list) or len(data) != 3:
        raise ValueError(
            f"Expected list of 3 insights, got {type(data).__name__} "
            f"with len {len(data) if isinstance(data, list) else 'N/A'}"
        )

    required_keys = {"icon", "title", "text"}
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} is not a dict: {item!r}")
        missing = required_keys - item.keys()
        if missing:
            raise ValueError(f"Item {i} missing keys: {missing}")
        # Truncate overlong strings at UI boundary rather than crashing
        if len(item.get("title", "")) > 60:
            item["title"] = item["title"][:57] + "..."
        if len(item.get("text", "")) > 400:
            item["text"] = item["text"][:397] + "..."

    return data


async def get_insights(user, recent_activities: list) -> list[dict]:
    """
    Returns 3 personalised coaching insights.
    Cached per user for 1 hour (5 min on Groq failure).
    Falls back to generic tips on any Groq error.
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
        logger.warning(
            "Groq insights error for user %s: %s. Using fallback.", user.id, exc
        )
        # Cache with a 55-minute-old timestamp → retries Groq in ~5 minutes,
        # avoiding a thundering herd when the API is down.
        _insights_cache[cache_key] = (
            datetime.utcnow() - timedelta(minutes=55),
            FALLBACK_INSIGHTS,
        )
        return FALLBACK_INSIGHTS


async def _generate_insights(user, activities: list, cache_key: str) -> list[dict]:
    """Generate 3 coaching insights from Groq. Only aggregate stats in the prompt."""
    stats = _build_stats(user, activities)
    prompt = _build_prompt(stats)

    client = get_groq_client()
    raw_text = ""
    last_err: Exception | None = None

    for model_name in GROQ_MODELS:
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
            logger.debug("Model %s failed: %s", model_name, e)
            last_err = e
            continue

    if not raw_text.strip():
        raise last_err or RuntimeError("All Groq models returned empty responses")

    data = _parse_and_validate(raw_text)
    _insights_cache[cache_key] = (datetime.utcnow(), data)
    return data
