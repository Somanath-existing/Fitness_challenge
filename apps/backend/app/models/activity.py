"""Activity table definition."""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Activity(SQLModel, table=True):
    __tablename__ = "activities"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="users.id", max_length=36, index=True)

    # Sport and metric — validated at application layer
    sport: str = Field(max_length=20, index=True)
    metric_type: str = Field(max_length=20)

    # Raw value preserved as-is for audit
    raw_value: str = Field(max_length=20)
    # Normalised (floored) value for charts
    normalized_value: float
    points_awarded: int = Field(index=True)

    # Optional user-supplied metadata (sanitised before store)
    title: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=100)
    source: str = Field(default="manual", max_length=20)

    # Timestamps — logged_at is user-supplied (validated no future), created_at is server-set
    logged_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        # ON DELETE CASCADE handled via FK constraint
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_activities_user_id",
        ),
    )
