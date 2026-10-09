"""Challenge and participation tables."""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Challenge(SQLModel, table=True):
    __tablename__ = "challenges"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    title: str = Field(max_length=100)
    description: Optional[str] = Field(default=None)

    # NULL creator_id = system/LLM generated
    creator_id: Optional[str] = Field(default=None, max_length=36)

    sport: Optional[str] = Field(default=None, max_length=20)
    metric_type: str = Field(max_length=20)
    target_value: float
    bonus_points: int = Field(default=0, ge=0)
    is_daily: bool = Field(default=False)
    difficulty: str = Field(default="medium", max_length=10)
    coach_note: Optional[str] = Field(default=None)

    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["creator_id"], ["users.id"],
            ondelete="SET NULL",
            name="fk_challenges_creator",
        ),
    )


class ChallengeParticipant(SQLModel, table=True):
    __tablename__ = "challenge_participants"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    challenge_id: str = Field(foreign_key="challenges.id", max_length=36)
    user_id: str = Field(foreign_key="users.id", max_length=36)

    # invited | accepted | completed | declined
    status: str = Field(default="accepted", max_length=10)
    progress: float = Field(default=0.0)
    completed_at: Optional[datetime] = Field(default=None)
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        sa.UniqueConstraint(
            "challenge_id", "user_id",
            name="uq_cp_challenge_user",
        ),
        sa.ForeignKeyConstraint(
            ["challenge_id"], ["challenges.id"],
            ondelete="CASCADE",
            name="fk_cp_challenge",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            ondelete="CASCADE",
            name="fk_cp_user",
        ),
    )
