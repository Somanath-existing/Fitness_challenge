"""Notification table."""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="users.id", max_length=36, index=True)

    # friend_request | challenge_invite | challenge_complete | daily_ready | badge_unlocked
    type: str = Field(max_length=30)
    payload: str = Field(default="{}")  # JSON string
    read: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            ondelete="CASCADE",
            name="fk_notifications_user",
        ),
    )
