"""
Seed script — populates the database with 10 users and 30 days of realistic activity data.
Run: python seed.py
Or automatically via Docker entrypoint.

Safe to run multiple times — checks for existing data first.
"""
from __future__ import annotations
import os, sys, random, json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.user import User
from app.models.activity import Activity
from app.services.scoring import calculate_points, SportType
from app.services.streak import compute_streak
from app.services.tiers import get_tier
from app.services.auth import hash_password

SEED_USERS = [
    {"first_name": "Alice",   "last_name": "Chen",     "timezone": "Asia/Kolkata",      "fitness_goal": 600},
    {"first_name": "Bob",     "last_name": "Patel",    "timezone": "Asia/Kolkata",      "fitness_goal": 500},
    {"first_name": "Priya",   "last_name": "Sharma",   "timezone": "Asia/Kolkata",      "fitness_goal": 700},
    {"first_name": "Marcus",  "last_name": "Webb",     "timezone": "America/New_York",  "fitness_goal": 400},
    {"first_name": "Sofia",   "last_name": "Rossi",    "timezone": "Europe/Rome",       "fitness_goal": 550},
    {"first_name": "Kenji",   "last_name": "Tanaka",   "timezone": "Asia/Tokyo",        "fitness_goal": 800},
    {"first_name": "Aisha",   "last_name": "Omar",     "timezone": "Africa/Nairobi",    "fitness_goal": 450},
    {"first_name": "Luca",    "last_name": "Bianchi",  "timezone": "Europe/Rome",       "fitness_goal": 500},
    {"first_name": "Mei",     "last_name": "Lin",      "timezone": "Asia/Shanghai",     "fitness_goal": 600},
    {"first_name": "Arjun",   "last_name": "Nair",     "timezone": "Asia/Kolkata",      "fitness_goal": 750},
]

# Sport → (metric_type, min_value, max_value, step)
SPORT_RANGES = {
    SportType.running:  ("distance_km",    1.0,  15.0,  0.5),
    SportType.walking:  ("distance_km",    0.5,  10.0,  0.5),
    SportType.cycling:  ("distance_km",    5.0,  50.0,  2.5),
    SportType.swimming: ("duration_minsec", 10,   60,    5),
    SportType.gym:      ("duration_minsec", 15,   90,    5),
    SportType.steps:    ("count",          2000, 18000, 500),
}


def random_metric_value(sport: SportType) -> str:
    metric_type, low, high, step = SPORT_RANGES[sport]
    if metric_type == "duration_minsec":
        mins = random.randrange(int(low), int(high), int(step))
        secs = random.choice([0, 15, 30, 45])
        return f"{mins}:{secs:02d}"
    elif metric_type == "count":
        return str(random.randrange(int(low), int(high), int(step)))
    else:
        val = round(random.uniform(low, high) / step) * step
        return str(round(val, 1))


def seed():
    create_db_and_tables()

    with Session(engine) as session:
        # Check if already seeded
        existing = session.exec(select(User)).first()
        if existing:
            # Backfill any seeded users missing password or username
            users_without_pwd = session.exec(select(User).where(User.hashed_password == None)).all()
            if users_without_pwd:
                default_pwd = hash_password("Password123!")
                for u in users_without_pwd:
                    uname = f"{u.first_name.lower()}_{u.last_name.lower()}"
                    if not u.username:
                        u.username = uname
                    if not u.email:
                        u.email = f"{uname}@example.com"
                    u.hashed_password = default_pwd
                    session.add(u)
                session.commit()
                print(f"Backfilled passwords for {len(users_without_pwd)} existing users.")
            print("Database already has users — seed complete.")
            return

        print("Seeding database with 10 users and 30 days of activity data…")

        for user_data in SEED_USERS:
            uname = f"{user_data['first_name'].lower()}_{user_data['last_name'].lower()}"
            user = User(
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                username=uname,
                email=f"{uname}@example.com",
                timezone=user_data["timezone"],
                fitness_goal=user_data["fitness_goal"],
                hashed_password=hash_password("Password123!"),
                badges="[]",
            )
            session.add(user)
            session.flush()  # Get the UUID

            # Generate 30 days of activity
            now = datetime.utcnow()
            sports_pool = list(SportType)

            for day_offset in range(30):
                # Each user logs 1–3 activities per day (random, some days skipped)
                if random.random() < 0.15:  # 15% chance of rest day
                    continue

                day = now - timedelta(days=day_offset)
                num_activities = random.randint(1, 2)

                for _ in range(num_activities):
                    sport = random.choice(sports_pool)
                    metric_type = SPORT_RANGES[sport][0]
                    raw_value = random_metric_value(sport)

                    try:
                        result = calculate_points(sport, raw_value)
                    except ValueError:
                        continue

                    logged_at = day.replace(
                        hour=random.randint(6, 20),
                        minute=random.randint(0, 59),
                        second=0,
                        microsecond=0,
                    )

                    activity = Activity(
                        user_id=user.id,
                        sport=sport.value,
                        metric_type=metric_type,
                        raw_value=str(raw_value),
                        normalized_value=result["normalized"],
                        points_awarded=result["points"],
                        source="manual",
                        logged_at=logged_at,
                    )
                    session.add(activity)
                    user.total_points += result["points"]

            # Compute streak (simplified — uses most recent dates)
            session.flush()

            # Give users realistic streaks
            user.current_streak = random.randint(1, 15)

            print(f"  ✓ {user.first_name} {user.last_name}: {user.total_points} pts, tier={get_tier(user.total_points)}")

        session.commit()
        print("\nSeed complete!")


if __name__ == "__main__":
    seed()
