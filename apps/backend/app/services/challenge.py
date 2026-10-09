"""
Daily challenge generation using Groq AI (llama-3.3-70b-versatile).

Security: user-supplied text (bio, notes, titles) is NEVER included in prompts.
Only aggregate computed statistics (sport counts, streak, tier) go into the prompt.
This eliminates prompt injection surface entirely.

Caching: in-memory per user, 24h TTL. Resets on server restart.
(Production improvement: use Redis for cross-restart persistence.)
"""
from __future__ import annotations
import json
import os
import random
import logging
from datetime import datetime, timedelta
from groq import Groq

from app.services.tiers import get_tier

logger = logging.getLogger(__name__)

# Lazy-init client — avoids crash if GROQ_API_KEY is not set in test environment
_client: Groq | None = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=api_key)
    return _client


# In-memory 24h cache: { user_id: (generated_at: datetime, challenge: dict) }
_challenge_cache: dict[str, tuple[datetime, dict]] = {}

# Static fallback pool — always available even if Groq is down
FALLBACK_CHALLENGES = [
    {
        "title": "Morning kilometre walk",
        "description": "Start your day with an easy 1km walk to build the habit.",
        "sport": "walking",
        "metric": {"type": "distance_km", "target": 1},
        "bonus_points": 0,
        "difficulty": "easy",
        "coach_note": "Focus on posture — shoulders back, head up.",
    },
    {
        "title": "20-minute gym session",
        "description": "Any 20 minutes of gym work counts. Show up.",
        "sport": "gym",
        "metric": {"type": "duration_minsec", "target": "20:00"},
        "bonus_points": 0,
        "difficulty": "easy",
        "coach_note": "Compound movements (squats, press, row) give the most return per minute.",
    },
    {
        "title": "5km run",
        "description": "A classic distance for a reason. Steady pace wins.",
        "sport": "running",
        "metric": {"type": "distance_km", "target": 5},
        "bonus_points": 0,
        "difficulty": "medium",
        "coach_note": "Run at a pace where you can hold a broken conversation.",
    },
    {
        "title": "10,000 steps",
        "description": "The gold standard daily step target.",
        "sport": "steps",
        "metric": {"type": "count", "target": 10000},
        "bonus_points": 0,
        "difficulty": "medium",
        "coach_note": "Break it into three 3,000-step chunks across the day if needed.",
    },
    {
        "title": "30-minute swim",
        "description": "Low impact, full body. Perfect active recovery.",
        "sport": "swimming",
        "metric": {"type": "duration_minsec", "target": "30:00"},
        "bonus_points": 0,
        "difficulty": "medium",
        "coach_note": "Mix strokes — freestyle, backstroke, breaststroke — to work different muscle groups.",
    },
    {
        "title": "15km cycling ride",
        "description": "A solid mid-week ride to keep the legs turning.",
        "sport": "cycling",
        "metric": {"type": "distance_km", "target": 15},
        "bonus_points": 0,
        "difficulty": "medium",
        "coach_note": "Maintain 80-90 RPM cadence for efficiency.",
    },
]


import re

async def get_daily_challenge(user, recent_activities: list) -> dict:
    """
    Returns today's challenge for the user.
    Cached 24h per user. Falls back to static pool on Groq failure.
    """
    cache_key = user.id
    cached = _challenge_cache.get(cache_key)
    if cached:
        generated_at, data = cached
        if datetime.utcnow() - generated_at < timedelta(hours=24):
            return data

    try:
        return await _generate_from_groq(user, recent_activities, cache_key)
    except Exception as exc:
        logger.warning("Groq API error for user %s: %s. Using fallback challenge.", user.id, exc)
        fallback = random.choice(FALLBACK_CHALLENGES)
        # Note: Do not cache fallback for 24h so future requests can retry Groq AI
        return fallback


async def _generate_from_groq(user, activities: list, cache_key: str) -> dict:
    """
    Build aggregate stats from user history, call Groq, parse JSON response.

    SECURITY: Only numeric/enum stats go into the prompt.
    User text (bio, notes, titles) is never included.
    """
    # Build sport frequency map from activity objects
    sport_freq: dict[str, int] = {}
    for a in activities:
        sport_freq[a.sport] = sport_freq.get(a.sport, 0) + 1

    all_sports = ["running", "walking", "cycling", "gym", "swimming", "steps"]
    neglected = [s for s in all_sports if s not in sport_freq]
    strongest = max(sport_freq, key=sport_freq.get) if sport_freq else "none"
    last_7_sports = [a.sport for a in activities[:7]]

    tier = get_tier(user.total_points)

    prompt = f"""You are a fitness coach. Return ONLY valid JSON - no preamble, no markdown fences, no explanation.

Context:
- tier: {tier}
- streak: {user.current_streak} days
- strongest_sport: {strongest}
- neglected_sports: {neglected}
- last_7_activities_sports: {last_7_sports}

Rules:
1. Challenge must be achievable in one session
2. Prefer a neglected sport if there are any
3. Scale difficulty to tier (rookie=easy, elite=hard)
4. If streak > 5, protect it - don't suggest something risky
5. Be specific, not vague

Return exactly this JSON shape (no other keys):
{{
  "title": "max 6 words",
  "description": "one motivating sentence",
  "sport": "one of: running|walking|cycling|gym|swimming|steps",
  "metric": {{"type": "distance_km|duration_minsec|count", "target": 5}},
  "bonus_points": 0,
  "difficulty": "easy|medium|hard",
  "coach_note": "one practical technique tip"
}}"""

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
                max_tokens=1000,
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

    # Extract JSON object bounds if extra text is present
    obj_match = re.search(r"\{[\s\S]*\}", cleaned)
    if obj_match:
        cleaned = obj_match.group(0)

    data = json.loads(cleaned)

    # Force bonus_points to 0 so all scores strictly match the actual activity logic
    data["bonus_points"] = 0

    # Validate required keys are present before caching
    required = {"title", "description", "sport", "metric", "bonus_points", "difficulty", "coach_note"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Groq response missing keys: {missing}")

    _challenge_cache[cache_key] = (datetime.utcnow(), data)
    return data
