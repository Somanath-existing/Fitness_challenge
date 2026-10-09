"""
SQLModel table definitions — single source of truth for DB schema.
Import order matters for FK resolution.
"""
from .user import User
from .activity import Activity
from .friendship import Friendship
from .challenge import Challenge, ChallengeParticipant
from .notification import Notification

__all__ = [
    "User",
    "Activity",
    "Friendship",
    "Challenge",
    "ChallengeParticipant",
    "Notification",
]
