"""
Pydantic v2 request / response schemas.
All validation runs BEFORE route handlers — invalid input never reaches business logic.
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import pytz

from app.services.scoring import SportType, SPORT_METRIC_MAP


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=30,
        pattern=r"^[a-z0-9_]+$",
        description="Lowercase alphanumeric and underscores only",
    )
    timezone: str = Field(default="UTC", max_length=50)
    fitness_goal: Optional[int] = Field(None, gt=0, description="Weekly points target")
    bio: Optional[str] = Field(None, max_length=160)
    password: Optional[str] = Field(None, min_length=8, max_length=128, description="Plaintext password")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_and_validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank or whitespace only")
        # Reject names with dangerous characters
        if re.search(r'[<>&"\']', v):
            raise ValueError("Name contains invalid characters")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone '{v}'. Use IANA format e.g. 'Asia/Kolkata'")
        return v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().lower()
        return v if v else None

    @field_validator("username")
    @classmethod
    def clean_username(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().lower()
        return v if v else None

    @field_validator("bio")
    @classmethod
    def sanitise_bio(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        # Strip HTML tags — bleach.clean used at storage layer too
        v = re.sub(r"<[^>]+>", "", v)
        return v.strip()


class UserResponse(BaseModel):
    """Full profile — only returned to the owner (authenticated user)."""
    user_id: str
    first_name: str
    last_name: str
    email: Optional[str]  # Only returned to the account owner
    username: Optional[str]
    total_points: int
    current_streak: int
    tier: str
    created_at: datetime

    class Config:
        from_attributes = True


class PublicUserResponse(BaseModel):
    """Public profile — email is intentionally excluded to prevent enumeration."""
    user_id: str
    first_name: str
    username: Optional[str]
    total_points: int
    current_streak: int
    tier: str
    bio: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: Optional[str] = Field(None, description="Username or email")
    email: Optional[EmailStr] = None
    identifier: Optional[str] = Field(None, description="Username or email identifier")
    password: str = Field(..., min_length=1, description="Plaintext password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

class MetricInput(BaseModel):
    type: str = Field(
        ...,
        pattern=r"^(distance_km|duration_minsec|count)$",
        description="distance_km | duration_minsec | count",
    )
    value: Any = Field(..., description="float for km, 'MM:SS' for duration, int for steps")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        # Reject obviously bad values early
        if v is None:
            raise ValueError("metric.value is required")
        return v


class ActivityCreate(BaseModel):
    # user_id is ignored in production; server enforces JWT identity.
    user_id: Optional[str] = None
    sport: SportType
    metric: MetricInput
    title: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    source: str = Field(
        "manual",
        pattern=r"^(manual|apple_watch|garmin|fitbit)$",
    )
    logged_at: Optional[datetime] = None

    @field_validator("logged_at")
    @classmethod
    def no_future_dates(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v > datetime.utcnow():
            raise ValueError("logged_at cannot be in the future")
        return v

    @model_validator(mode="after")
    def validate_sport_metric_match(self) -> "ActivityCreate":
        expected = SPORT_METRIC_MAP.get(self.sport)
        if expected and self.metric.type != expected:
            raise ValueError(
                f"Sport '{self.sport}' requires metric type '{expected}', got '{self.metric.type}'"
            )
        return self

    @field_validator("notes", "title", "location")
    @classmethod
    def sanitise_text(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        # Strip HTML tags
        v = re.sub(r"<[^>]+>", "", v)
        return v.strip()


class ActivityResponse(BaseModel):
    activity_id: str
    points_awarded: int
    user_total_points: int
    current_streak: int
    new_badges: List[str]
    is_personal_best: bool


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

class LeaderboardEntry(BaseModel):
    rank: int
    rank_delta: int
    user_id: str
    first_name: str
    username: Optional[str]
    total_points: int
    tier: str
    current_streak: int
    badges: List[str]


class LeaderboardResponse(BaseModel):
    data: List[LeaderboardEntry]
    total: int
    generated_at: datetime


# ---------------------------------------------------------------------------
# Friends
# ---------------------------------------------------------------------------

class FriendRequest(BaseModel):
    identifier: Optional[str] = Field(None, description="Username or user UUID of the friend")
    username: Optional[str] = Field(None, description="Friend's username")
    addressee_id: Optional[str] = Field(None, description="Friend's user ID or username")

    @model_validator(mode="after")
    def validate_has_identifier(self) -> "FriendRequest":
        target = self.identifier or self.username or self.addressee_id
        if not target or not target.strip():
            raise ValueError("Must provide friend's username or user ID")
        return self


class FriendRespond(BaseModel):
    action: str = Field(..., pattern=r"^(accept|decline)$")


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

class ChallengeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sport: Optional[SportType] = None
    metric_type: str = Field(..., pattern=r"^(points|distance_km|duration_minsec|count)$")
    target_value: float = Field(..., gt=0)
    bonus_points: int = Field(0, ge=0)
    difficulty: str = Field("medium", pattern=r"^(easy|medium|hard)$")
    end_date: Optional[datetime] = None
    invitee_ids: Optional[List[str]] = Field(default_factory=list)
    creator_id: Optional[str] = Field(None, description="Creator user ID if provided in body")

    @field_validator("end_date")
    @classmethod
    def end_date_must_be_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v <= datetime.utcnow():
            raise ValueError("end_date must be in the future")
        return v

    @model_validator(mode="after")
    def validate_sport_metric_match(self) -> "ChallengeCreate":
        if self.sport:
            expected = SPORT_METRIC_MAP.get(self.sport)
            if self.metric_type != "points" and self.metric_type != expected:
                raise ValueError(
                    f"Sport '{self.sport.value}' only supports metric '{expected}' or 'points', got '{self.metric_type}'"
                )
        return self


class ChallengeRespond(BaseModel):
    action: str = Field(..., pattern=r"^(accept|decline)$")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class SportBreakdownItem(BaseModel):
    sport: str
    total_points: int
    percentage: float


class WeeklyTrendItem(BaseModel):
    week: str
    points: int


class HeatmapItem(BaseModel):
    date: str
    points: int


class GoalProgress(BaseModel):
    target: int
    achieved: int
    percentage: float


class DashboardResponse(BaseModel):
    user: dict
    sport_breakdown: List[SportBreakdownItem]
    weekly_trend: List[WeeklyTrendItem]
    heatmap: List[HeatmapItem]
    recent_activities: List[dict]
    goal_progress: Optional[GoalProgress]
