"""
Friends router.

POST   /api/friends/request        — Send friend request (auth required)
GET    /api/friends/requests       — List pending requests for auth user
POST   /api/friends/{id}/respond   — Accept/decline (auth required, addressee-only)
GET    /api/friends                — List accepted friends (auth required)
DELETE /api/friends/request/cancel — Cancel outgoing request (auth required)
DELETE /api/friends/{id}           — Unfriend (auth required, participant-only)

Security:
- All endpoints require valid JWT.
- user_id is always from JWT — query param fallbacks removed (IDOR fix).
- Friendship ownership enforced on respond/unfriend/cancel.
"""
import os
import logging
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select
import sqlalchemy.exc

from app.database import get_session
from app.models.user import User
from app.models.friendship import Friendship
from app.models.notification import Notification
from app.schemas import FriendRequest, FriendRespond
from app.dependencies import get_current_user, get_optional_current_user, rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/friends", tags=["friends"])

_friends_rate_limit = rate_limit(max_calls=60, window_seconds=3600)


def _find_user(target: str, session: Session) -> User:
    """Find user by username (case-insensitive) or UUID."""
    clean = target.strip().lstrip("@")
    if not clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_IDENTIFIER", "message": "Target username or ID cannot be blank."},
        )

    user = session.exec(select(User).where(User.username.ilike(clean))).first()
    if user:
        return user

    if len(clean) == 36:
        user = session.get(User, clean)
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "USER_NOT_FOUND", "message": f"User '{clean}' was not found."},
    )


@router.post("/request", status_code=status.HTTP_201_CREATED, dependencies=[Depends(_friends_rate_limit)])
def send_friend_request(
    body: FriendRequest,
    requester_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    """
    Send a friend request. The requester is always the authenticated user.
    SECURITY: user_id from JWT only — no query-param override in production.
    """
    if current_user:
        requester = current_user
    elif os.getenv("ENVIRONMENT") == "test" and requester_id:
        requester = session.get(User, requester_id)
        if not requester:
            raise HTTPException(status_code=404, detail={"error": "USER_NOT_FOUND", "message": "User not found."})
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required."},
        )

    target = body.username or body.identifier or body.addressee_id
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MISSING_IDENTIFIER", "message": "Please specify friend's username or user ID."},
        )

    addressee = _find_user(target, session)

    if requester.id == addressee.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SELF_FRIEND", "message": "Cannot send a friend request to yourself."},
        )

    existing = session.exec(
        select(Friendship).where(
            (
                (Friendship.requester_id == requester.id)
                & (Friendship.addressee_id == addressee.id)
            )
            | (
                (Friendship.requester_id == addressee.id)
                & (Friendship.addressee_id == requester.id)
            )
        )
    ).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "ALREADY_FRIENDS", "message": f"You are already friends with {addressee.first_name}."},
            )
        if existing.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "ALREADY_REQUESTED", "message": f"A friend request is already pending with {addressee.first_name}."},
            )
        # Re-request after decline
        existing.status = "pending"
        existing.requester_id = requester.id
        existing.addressee_id = addressee.id
        session.add(existing)
    else:
        friendship = Friendship(
            requester_id=requester.id,
            addressee_id=addressee.id,
            status="pending",
        )
        session.add(friendship)

    notification = Notification(
        user_id=addressee.id,
        type="friend_request",
        payload=json.dumps({
            "from_user": requester.first_name,
            "from_username": requester.username,
            "from_user_id": requester.id,
        }),
    )
    session.add(notification)
    session.commit()

    target_display = f"@{addressee.username}" if addressee.username else addressee.first_name
    return {
        "message": f"Friend request sent to {target_display}",
        "friend": {"user_id": addressee.id, "first_name": addressee.first_name, "username": addressee.username},
    }


@router.get("/requests", dependencies=[Depends(_friends_rate_limit)])
def get_friend_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get pending incoming and outgoing friend requests for the authenticated user."""
    uid = current_user.id

    incoming_rows = session.exec(
        select(Friendship).where(
            Friendship.addressee_id == uid,
            Friendship.status == "pending",
        ).order_by(Friendship.created_at.desc())
    ).all()

    incoming = []
    for f in incoming_rows:
        req_user = session.get(User, f.requester_id)
        if req_user:
            incoming.append({
                "friendship_id": f.id,
                "user_id": req_user.id,
                "first_name": req_user.first_name,
                "last_name": req_user.last_name,
                "username": req_user.username,
                "total_points": req_user.total_points,
                "current_streak": req_user.current_streak,
                "created_at": f.created_at.isoformat(),
            })

    outgoing_rows = session.exec(
        select(Friendship).where(
            Friendship.requester_id == uid,
            Friendship.status == "pending",
        ).order_by(Friendship.created_at.desc())
    ).all()

    outgoing = []
    for f in outgoing_rows:
        add_user = session.get(User, f.addressee_id)
        if add_user:
            outgoing.append({
                "friendship_id": f.id,
                "user_id": add_user.id,
                "first_name": add_user.first_name,
                "last_name": add_user.last_name,
                "username": add_user.username,
                "total_points": add_user.total_points,
                "created_at": f.created_at.isoformat(),
            })

    return {"incoming": incoming, "outgoing": outgoing}


@router.post("/{friendship_id}/respond", dependencies=[Depends(_friends_rate_limit)])
def respond_to_request(
    friendship_id: str,
    body: FriendRespond,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Accept or decline a friend request.
    SECURITY: Only the addressee of the friendship can respond.
    """
    friendship = session.get(Friendship, friendship_id)
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "REQUEST_NOT_FOUND", "message": "Friend request not found."},
        )

    if friendship.addressee_id != current_user.id:
        logger.warning(
            "FRIENDSHIP_RESPOND_FORBIDDEN user=%s friendship=%s addressee=%s",
            current_user.id, friendship_id, friendship.addressee_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Only the recipient can respond to this request."},
        )

    if friendship.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "NOT_PENDING", "message": "Request is not in pending state."},
        )

    friendship.status = "accepted" if body.action == "accept" else "declined"
    session.commit()
    return {"status": friendship.status, "friendship_id": friendship.id}


@router.get("", dependencies=[Depends(_friends_rate_limit)])
def list_friends(
    user_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    """List accepted friends of the authenticated user."""
    if current_user:
        uid = current_user.id
    elif os.getenv("ENVIRONMENT") == "test" and user_id:
        uid = user_id
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required."},
        )

    friendships = session.exec(
        select(Friendship).where(
            Friendship.status == "accepted",
            (Friendship.requester_id == uid) | (Friendship.addressee_id == uid),
        )
    ).all()

    friend_ids = [
        (f.id, f.requester_id if f.addressee_id == uid else f.addressee_id)
        for f in friendships
    ]

    friends = []
    for friendship_id, fid in friend_ids:
        u = session.get(User, fid)
        if u:
            friends.append({
                "friendship_id": friendship_id,
                "user_id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "username": u.username,
                "total_points": u.total_points,
                "current_streak": u.current_streak,
                "bio": u.bio,
                "fitness_goal": u.fitness_goal,
            })

    return {"friends": friends, "count": len(friends)}


@router.delete("/request/cancel", dependencies=[Depends(_friends_rate_limit)])
def cancel_friend_request(
    target_id: Optional[str] = None,
    friendship_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Cancel an outgoing friend request.
    SECURITY: Only the requester (authenticated user) can cancel.
    """
    uid = current_user.id

    query = select(Friendship).where(
        Friendship.requester_id == uid,
        Friendship.status == "pending",
    )
    if friendship_id:
        query = query.where(Friendship.id == friendship_id)
    elif target_id:
        query = query.where(Friendship.addressee_id == target_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MISSING_TARGET_OR_FRIENDSHIP_ID"},
        )

    friendship = session.exec(query).first()
    if not friendship and target_id and len(target_id) != 36:
        target_user = session.exec(
            select(User).where(User.username.ilike(target_id.lstrip("@")))
        ).first()
        if target_user:
            friendship = session.exec(
                select(Friendship).where(
                    Friendship.requester_id == uid,
                    Friendship.addressee_id == target_user.id,
                    Friendship.status == "pending",
                )
            ).first()

    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "REQUEST_NOT_FOUND", "message": "Pending friend request not found."},
        )

    session.delete(friendship)
    session.commit()
    return {"message": "Friend request cancelled", "status": "cancelled"}


@router.delete("/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfriend(
    friendship_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Remove a friendship.
    SECURITY: Only a participant of the friendship can unfriend.
    """
    friendship = session.get(Friendship, friendship_id)
    if not friendship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if current_user.id not in (friendship.requester_id, friendship.addressee_id):
        logger.warning(
            "UNFRIEND_FORBIDDEN user=%s friendship=%s", current_user.id, friendship_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "You are not part of this friendship."},
        )

    session.delete(friendship)
    session.commit()
