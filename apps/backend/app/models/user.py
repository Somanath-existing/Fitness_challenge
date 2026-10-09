"""User table definition."""
import uuid
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field, Column, String
import sqlalchemy as sa


class User(SQLModel, table=True):
    __tablename__ = "users"

    # Primary key — UUID, never auto-increment
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )

    first_name: str = Field(max_length=50, nullable=False)
    last_name: str = Field(max_length=50, nullable=False)

    # Optional unique fields
    email: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = Field(default=None, max_length=30)
    hashed_password: Optional[str] = Field(default=None, max_length=255)

    # Profile
    timezone: str = Field(default="UTC", max_length=50)
    fitness_goal: Optional[int] = Field(default=None, gt=0)
    bio: Optional[str] = Field(default=None, max_length=160)

    # Denormalised counters — updated atomically on each activity insert
    total_points: int = Field(default=0, index=True)
    current_streak: int = Field(default=0)
    last_active_date: Optional[date] = Field(default=None)

    # Badges stored as JSON array string e.g. '["7day","marathon"]'
    badges: str = Field(default="[]", max_length=2000)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        # Duplicate detection: case-insensitive composite unique on name
        sa.Index(
            "uq_users_name_ci",
            sa.func.lower(sa.text("first_name")),
            sa.func.lower(sa.text("last_name")),
            unique=True,
        ),
        # Case-insensitive unique email index
        sa.Index(
            "uq_users_email_ci",
            sa.func.lower(sa.text("email")),
            unique=True,
            postgresql_where=sa.text("email IS NOT NULL AND email != ''"),
        ),
        # Case-insensitive unique username index
        sa.Index(
            "uq_users_username_ci",
            sa.func.lower(sa.text("username")),
            unique=True,
            postgresql_where=sa.text("username IS NOT NULL AND username != ''"),
        ),
        # Descending index for O(1) leaderboard scan
        sa.Index("ix_users_total_points_desc", sa.text("total_points DESC")),
    )
