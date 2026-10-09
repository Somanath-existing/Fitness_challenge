"""Friendship table — bidirectional friend graph."""
import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Friendship(SQLModel, table=True):
    __tablename__ = "friendships"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    requester_id: str = Field(foreign_key="users.id", max_length=36)
    addressee_id: str = Field(foreign_key="users.id", max_length=36)

    # pending | accepted | declined | blocked
    status: str = Field(default="pending", max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        # Prevent duplicate requests (both directions)
        sa.UniqueConstraint(
            "requester_id", "addressee_id",
            name="uq_friendships_pair",
        ),
        # Prevent self-friend — enforced at app layer too
        sa.CheckConstraint(
            "requester_id != addressee_id",
            name="ck_friendships_no_self",
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"], ["users.id"],
            ondelete="CASCADE",
            name="fk_friendships_requester",
        ),
        sa.ForeignKeyConstraint(
            ["addressee_id"], ["users.id"],
            ondelete="CASCADE",
            name="fk_friendships_addressee",
        ),
    )
