"""
Challenges router.

GET  /api/challenges/daily/{user_id}  — AI daily challenge (auth required, ownership enforced)
GET  /api/challenges                  — List user's challenges (auth required)
POST /api/challenges                  — Create a challenge (auth required)
GET  /api/challenges/{id}             — Get challenge details (auth required)
POST /api/challenges/{id}/join        — Join a challenge (auth required)
POST /api/challenges/{id}/respond     — Accept/decline invite (auth required, participant check)
DELETE /api/challenges/{id}           — Delete challenge (auth required, creator-only)

Security:
- All endpoints require valid JWT.
- user_id is always taken from JWT (never from query params or body).
- IDOR: /daily/{user_id} enforces ownership so users only get their own daily challenge.
- creator-only delete enforced.
- AI generation rate-limited: 10 req/hr/IP.
"""
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User
from app.models.activity import Activity
from app.models.challenge import Challenge, ChallengeParticipant
from app.models.notification import Notification
from app.schemas import ChallengeCreate, ChallengeRespond
from app.services.challenge import (
    get_daily_challenge,
    get_fallback_challenge,
    validate_daily_challenge,
)
from app.dependencies import get_current_user, require_self, rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

# AI daily challenge is expensive — rate limit strictly
_daily_challenge_rate_limit = rate_limit(max_calls=10, window_seconds=3600)
_challenge_rate_limit = rate_limit(max_calls=60, window_seconds=3600)


@router.get(
    "/daily/{user_id}",
    dependencies=[Depends(_daily_challenge_rate_limit)],
)
async def daily_challenge(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Returns today's AI-generated challenge for the authenticated user.
    SECURITY: Enforces ownership — you can only fetch your own daily challenge.
    Cached 24h. Falls back to static pool on Groq failure.
    """
    require_self(user_id, current_user)

    target_id = current_user.id if user_id == "me" else user_id
    user = current_user if user_id == "me" else session.get(User, target_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # ── Check for existing daily challenge today ──────────────────────────────
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    existing_part = session.exec(
        select(ChallengeParticipant)
        .join(Challenge, Challenge.id == ChallengeParticipant.challenge_id)
        .where(
            ChallengeParticipant.user_id == user_id,
            Challenge.is_daily == True,
            Challenge.created_at >= today_start,
        )
    ).first()

    if existing_part:
        ch = session.get(Challenge, existing_part.challenge_id)
        if ch:
            existing_data = {
                "sport": ch.sport,
                "metric": {"type": ch.metric_type, "target": ch.target_value},
            }
            try:
                validate_daily_challenge(existing_data)
            except ValueError as exc:
                logger.warning(
                    "Replacing invalid saved daily challenge %s: %s",
                    ch.id,
                    exc,
                )
                fallback = get_fallback_challenge()
                fallback_metric = fallback["metric"]
                fallback_target = fallback_metric["target"]
                if fallback_metric["type"] == "duration_minsec" and isinstance(fallback_target, str):
                    minutes, seconds = fallback_target.split(":")
                    fallback_target_value = float(minutes) + float(seconds) / 60
                else:
                    fallback_target_value = float(fallback_target)

                ch.title = fallback["title"]
                ch.description = fallback["description"]
                ch.sport = fallback["sport"]
                ch.metric_type = fallback_metric["type"]
                ch.target_value = fallback_target_value
                ch.difficulty = fallback["difficulty"]
                ch.coach_note = fallback["coach_note"]
                existing_part.progress = 0
                existing_part.status = "accepted"
                session.add(ch)
                session.add(existing_part)
                session.commit()
                session.refresh(ch)

            return {
                "title": ch.title,
                "description": ch.description,
                "sport": ch.sport,
                "difficulty": ch.difficulty,
                "metric": {"type": ch.metric_type, "target": ch.target_value},
                "coach_note": ch.coach_note,
                "challenge_id": ch.id,
                "my_progress": existing_part.progress,
                "my_status": existing_part.status,
            }

    # Fetch last 30 days of activity for context
    cutoff = datetime.utcnow() - timedelta(days=30)
    recent = session.exec(
        select(Activity)
        .where(Activity.user_id == user_id, Activity.logged_at >= cutoff)
        .order_by(Activity.logged_at.desc())  # type: ignore[union-attr]
    ).all()

    challenge_data = await get_daily_challenge(user, recent)

    # Build the challenge DB record
    metric = challenge_data.get("metric", {})
    metric_type = metric.get("type", "distance_km")
    target_raw = metric.get("target", 1)

    if metric_type == "duration_minsec" and isinstance(target_raw, str) and ":" in str(target_raw):
        parts = str(target_raw).split(":")
        target_value = float(parts[0]) + float(parts[1]) / 60
    else:
        try:
            target_value = float(target_raw)
        except (ValueError, TypeError):
            target_value = 1.0

    new_challenge = Challenge(
        title=challenge_data["title"],
        description=challenge_data.get("description"),
        creator_id=None,
        sport=challenge_data.get("sport"),
        metric_type=metric_type,
        target_value=target_value,
        bonus_points=0,
        difficulty=challenge_data.get("difficulty", "medium"),
        coach_note=challenge_data.get("coach_note"),
        is_daily=True,
        end_date=today_end,
    )
    session.add(new_challenge)
    session.flush()

    participant = ChallengeParticipant(
        challenge_id=new_challenge.id,
        user_id=user_id,
        status="accepted",
    )
    session.add(participant)
    session.commit()
    session.refresh(new_challenge)

    challenge_data["challenge_id"] = new_challenge.id
    challenge_data["my_progress"] = 0.0
    challenge_data["my_status"] = "accepted"
    return challenge_data


@router.get("", dependencies=[Depends(_challenge_rate_limit)])
def list_challenges(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List all challenges for the authenticated user (owned or participating)."""
    uid = current_user.id

    participations = session.exec(
        select(ChallengeParticipant).where(ChallengeParticipant.user_id == uid)
    ).all()

    created_challenges = session.exec(
        select(Challenge).where(Challenge.creator_id == uid)
    ).all()

    challenge_ids = {p.challenge_id for p in participations} | {c.id for c in created_challenges}
    part_map = {p.challenge_id: p for p in participations}

    challenges = []
    for cid in challenge_ids:
        ch = session.get(Challenge, cid)
        if not ch or ch.is_daily:
            continue

        creator = session.get(User, ch.creator_id) if ch.creator_id else None
        my_part = part_map.get(ch.id)

        all_parts = session.exec(
            select(ChallengeParticipant).where(ChallengeParticipant.challenge_id == ch.id)
        ).all()

        participants_info = []
        for p in all_parts:
            u = session.get(User, p.user_id)
            participants_info.append({
                "user_id": p.user_id,
                "first_name": u.first_name if u else "Athlete",
                "username": u.username if u else None,
                "status": p.status,
                "progress": p.progress,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
            })

        challenges.append({
            "id": ch.id,
            "title": ch.title,
            "description": ch.description,
            "sport": ch.sport,
            "metric_type": ch.metric_type,
            "target_value": ch.target_value,
            "bonus_points": ch.bonus_points,
            "difficulty": ch.difficulty,
            "creator_id": ch.creator_id,
            "creator_name": creator.first_name if creator else "AI Coach",
            "creator_username": creator.username if creator else None,
            "is_creator": ch.creator_id == uid,
            "my_status": my_part.status if my_part else ("accepted" if ch.creator_id == uid else "none"),
            "my_progress": my_part.progress if my_part else 0.0,
            "start_date": ch.start_date.isoformat() if ch.start_date else None,
            "end_date": ch.end_date.isoformat() if ch.end_date else None,
            "created_at": ch.created_at.isoformat() if ch.created_at else None,
            "is_daily": ch.is_daily,
            "participants": participants_info,
        })

    challenges.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"challenges": challenges, "count": len(challenges)}


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(_challenge_rate_limit)])
def create_challenge(
    body: ChallengeCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Create a new challenge.
    creator_id is always the authenticated user — body.creator_id is ignored.
    """
    cid = current_user.id  # Always from JWT — never from body or query param

    challenge = Challenge(
        title=body.title,
        description=body.description,
        creator_id=cid,
        sport=body.sport.value if body.sport else None,
        metric_type=body.metric_type,
        target_value=body.target_value,
        bonus_points=0,
        difficulty=body.difficulty,
        end_date=body.end_date,
    )
    session.add(challenge)

    # Creator auto-joins
    participant = ChallengeParticipant(
        challenge_id=challenge.id,
        user_id=cid,
        status="accepted",
    )
    session.add(participant)

    # Invite others (supports user IDs or @usernames)
    invited_users = []
    for invitee_ref in (body.invitee_ids or []):
        ref_str = str(invitee_ref).strip().lstrip("@")
        if not ref_str:
            continue
        invitee = None
        if len(ref_str) == 36:
            invitee = session.get(User, ref_str)
        if not invitee:
            invitee = session.exec(select(User).where(User.username.ilike(ref_str))).first()

        if not invitee or invitee.id == cid:
            continue

        cp = ChallengeParticipant(
            challenge_id=challenge.id,
            user_id=invitee.id,
            status="invited",
        )
        session.add(cp)

        notif = Notification(
            user_id=invitee.id,
            type="challenge_invite",
            payload=json.dumps({
                "challenge_title": body.title,
                "from_user": current_user.first_name,
                "from_username": current_user.username,
                "challenge_id": challenge.id,
            }),
        )
        session.add(notif)
        invited_users.append({
            "user_id": invitee.id,
            "first_name": invitee.first_name,
            "username": invitee.username,
        })

    session.commit()
    session.refresh(challenge)
    return {
        "challenge_id": challenge.id,
        "title": challenge.title,
        "invited_count": len(invited_users),
        "invited_users": invited_users,
    }


@router.get("/{challenge_id}", dependencies=[Depends(_challenge_rate_limit)])
def get_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get challenge details.
    Requires auth. Only participants or the creator can see the challenge.
    """
    challenge = session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Verify the requesting user is a participant or creator
    is_creator = challenge.creator_id == current_user.id
    participant_row = session.exec(
        select(ChallengeParticipant).where(
            ChallengeParticipant.challenge_id == challenge_id,
            ChallengeParticipant.user_id == current_user.id,
        )
    ).first()

    if not is_creator and not participant_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "You are not a participant in this challenge."},
        )

    participants = session.exec(
        select(ChallengeParticipant).where(ChallengeParticipant.challenge_id == challenge_id)
    ).all()

    return {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "sport": challenge.sport,
        "metric_type": challenge.metric_type,
        "target_value": challenge.target_value,
        "bonus_points": challenge.bonus_points,
        "difficulty": challenge.difficulty,
        "coach_note": challenge.coach_note,
        "start_date": challenge.start_date,
        "end_date": challenge.end_date,
        "participants": [
            {
                "user_id": p.user_id,
                "status": p.status,
                "progress": p.progress,
                "completed_at": p.completed_at,
            }
            for p in participants
        ],
    }


@router.post("/{challenge_id}/join", dependencies=[Depends(_challenge_rate_limit)])
def join_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Join a challenge. The joining user is always the authenticated user."""
    uid = current_user.id

    challenge = session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    existing = session.exec(
        select(ChallengeParticipant).where(
            ChallengeParticipant.challenge_id == challenge_id,
            ChallengeParticipant.user_id == uid,
        )
    ).first()

    if existing:
        if existing.status == "invited":
            existing.status = "accepted"
            session.commit()
            return {"message": "Challenge accepted"}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "ALREADY_PARTICIPATING"},
        )

    cp = ChallengeParticipant(
        challenge_id=challenge_id,
        user_id=uid,
        status="accepted",
    )
    session.add(cp)
    session.commit()
    return {"message": "Joined challenge"}


@router.post("/{challenge_id}/respond", dependencies=[Depends(_challenge_rate_limit)])
def respond_challenge(
    challenge_id: str,
    body: ChallengeRespond,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Accept or decline a challenge invite.
    SECURITY: Only the authenticated user can respond for themselves.
    """
    uid = current_user.id

    challenge = session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    cp = session.exec(
        select(ChallengeParticipant).where(
            ChallengeParticipant.challenge_id == challenge_id,
            ChallengeParticipant.user_id == uid,
        )
    ).first()

    if not cp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_A_PARTICIPANT", "message": "You are not invited to this challenge."},
        )

    cp.status = "accepted" if body.action == "accept" else "declined"
    session.commit()
    return {"message": f"Challenge {body.action}ed", "status": cp.status, "challenge_id": challenge_id}


@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Delete a challenge. Only the creator can delete it.
    SECURITY: Ownership enforced — 403 if requester is not the creator.
    """
    challenge = session.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if challenge.creator_id != current_user.id:
        logger.warning(
            "CHALLENGE_DELETE_FORBIDDEN user=%s challenge=%s creator=%s",
            current_user.id, challenge_id, challenge.creator_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Only the challenge creator can delete it."},
        )

    participants = session.exec(
        select(ChallengeParticipant).where(ChallengeParticipant.challenge_id == challenge_id)
    ).all()
    for p in participants:
        session.delete(p)
    session.delete(challenge)
    session.commit()
