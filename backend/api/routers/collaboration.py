"""
Collaboration API router for multi-user features.

This module provides endpoints for sharing resources, collaboration sessions,
comments, notifications, and activity logs.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import get_current_user, get_db
from core.exceptions import NotFoundException, PermissionDeniedException
from models.collaboration import AccessLevel, CollaborationType
from models.user import User
from services.collaboration.collaboration_service import CollaborationService

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# Pydantic models for API
class ShareResourceRequest(BaseModel):
    """Request model for sharing a resource."""
    resource_type: CollaborationType
    resource_id: str
    shared_with_user_id: str
    access_level: AccessLevel
    share_message: Optional[str] = None


class ShareResourceResponse(BaseModel):
    """Response model for shared resource."""
    id: str
    resource_type: CollaborationType
    resource_id: str
    owner_id: str
    shared_with_user_id: str
    access_level: AccessLevel
    share_message: Optional[str]
    is_active: bool
    created_at: str


class CollaborationSessionCreate(BaseModel):
    """Request model for creating a collaboration session."""
    session_name: str
    session_type: CollaborationType
    resource_id: Optional[str] = None
    max_participants: int = 10


class CollaborationSessionResponse(BaseModel):
    """Response model for collaboration session."""
    id: str
    session_name: str
    session_type: CollaborationType
    resource_id: Optional[str]
    created_by: str
    is_active: bool
    max_participants: int
    participant_count: int
    created_at: str


class CommentCreate(BaseModel):
    """Request model for creating a comment."""
    content: str
    parent_comment_id: Optional[str] = None


class CommentResponse(BaseModel):
    """Response model for comment."""
    id: str
    resource_type: CollaborationType
    resource_id: str
    author_id: str
    content: str
    is_edited: bool
    parent_comment_id: Optional[str]
    created_at: str
    author_name: str


class NotificationResponse(BaseModel):
    """Response model for notification."""
    id: str
    notification_type: str
    title: str
    message: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    is_read: bool
    action_url: Optional[str]
    priority: str
    created_at: str


class ActivityLogResponse(BaseModel):
    """Response model for activity log."""
    id: str
    user_id: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    description: str
    success: bool
    created_at: str
    user_name: str


# API Endpoints
@router.post("/share", response_model=ShareResourceResponse)
async def share_resource(
    request: ShareResourceRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Share a resource with another user.

    Grants specified access level to the target user for the given resource.
    """
    try:
        service = CollaborationService(db)

        share = service.share_resource(
            owner=current_user,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            shared_with_user_id=request.shared_with_user_id,
            access_level=request.access_level,
            share_message=request.share_message
        )

        return ShareResourceResponse.from_orm(share)

    except (NotFoundException, PermissionDeniedException) as e:
        raise HTTPException(status_code=403 if isinstance(e, PermissionDeniedException) else 404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share resource: {str(e)}")


@router.get("/shared", response_model=List[ShareResourceResponse])
async def get_shared_resources(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get all resources shared with the current user.
    """
    try:
        service = CollaborationService(db)
        shares = service.get_shared_resources(current_user)

        return [ShareResourceResponse.from_orm(share) for share in shares]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve shared resources: {str(e)}")


@router.delete("/share/{share_id}")
async def revoke_share(
    share_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Revoke a resource share.
    """
    try:
        service = CollaborationService(db)
        service.revoke_share(current_user, share_id)

        return {"message": "Share revoked successfully"}

    except (NotFoundException, PermissionDeniedException) as e:
        raise HTTPException(status_code=403 if isinstance(e, PermissionDeniedException) else 404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke share: {str(e)}")


@router.post("/sessions", response_model=CollaborationSessionResponse)
async def create_collaboration_session(
    request: CollaborationSessionCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Create a new collaboration session.
    """
    try:
        service = CollaborationService(db)

        session = service.create_collaboration_session(
            creator=current_user,
            session_name=request.session_name,
            session_type=request.session_type,
            resource_id=request.resource_id,
            max_participants=request.max_participants
        )

        # Get participant count
        participant_count = db.query(SessionParticipant).filter(
            and_(
                SessionParticipant.session_id == session.id,
                SessionParticipant.is_active == True
            )
        ).count()

        response = CollaborationSessionResponse.from_orm(session)
        response.participant_count = participant_count

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create collaboration session: {str(e)}")


@router.post("/sessions/{session_id}/join")
async def join_collaboration_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Join a collaboration session.
    """
    try:
        service = CollaborationService(db)
        participant = service.join_collaboration_session(current_user, session_id)

        return {
            "message": "Successfully joined session",
            "participant_id": str(participant.id),
            "role": participant.role
        }

    except (NotFoundException, PermissionDeniedException) as e:
        raise HTTPException(status_code=403 if isinstance(e, PermissionDeniedException) else 404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to join session: {str(e)}")


@router.post("/sessions/{session_id}/leave")
async def leave_collaboration_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Leave a collaboration session.
    """
    try:
        service = CollaborationService(db)
        service.leave_collaboration_session(current_user, session_id)

        return {"message": "Successfully left session"}

    except (NotFoundException, PermissionDeniedException) as e:
        raise HTTPException(status_code=403 if isinstance(e, PermissionDeniedException) else 404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to leave session: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_collaboration_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get details of a collaboration session.
    """
    try:
        from models.collaboration import CollaborationSession, SessionParticipant
        from sqlalchemy import and_

        session = db.query(CollaborationSession).filter(
            and_(
                CollaborationSession.id == session_id,
                CollaborationSession.is_active == True
            )
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Check if user is a participant
        participant = db.query(SessionParticipant).filter(
            and_(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == str(current_user.id),
                SessionParticipant.is_active == True
            )
        ).first()

        if not participant:
            raise HTTPException(status_code=403, detail="You are not a participant in this session")

        # Get participant count
        participant_count = db.query(SessionParticipant).filter(
            and_(
                SessionParticipant.session_id == session_id,
                SessionParticipant.is_active == True
            )
        ).count()

        response = CollaborationSessionResponse.from_orm(session)
        response.participant_count = participant_count

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.post("/comments", response_model=CommentResponse)
async def add_comment(
    request: CommentCreate,
    resource_type: CollaborationType = Query(..., description="Type of resource being commented on"),
    resource_id: str = Query(..., description="ID of the resource"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Add a comment to a resource.
    """
    try:
        service = CollaborationService(db)

        comment = service.add_comment(
            user=current_user,
            resource_type=resource_type,
            resource_id=resource_id,
            content=request.content,
            parent_comment_id=request.parent_comment_id
        )

        return CommentResponse(
            id=str(comment.id),
            resource_type=comment.resource_type,
            resource_id=comment.resource_id,
            author_id=comment.author_id,
            content=comment.content,
            is_edited=comment.is_edited,
            parent_comment_id=comment.parent_comment_id,
            created_at=comment.created_at.isoformat(),
            author_name=current_user.full_name
        )

    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


@router.get("/comments", response_model=List[CommentResponse])
async def get_comments(
    resource_type: CollaborationType = Query(..., description="Type of resource"),
    resource_id: str = Query(..., description="ID of the resource"),
    limit: int = Query(50, description="Maximum number of comments"),
    offset: int = Query(0, description="Number of comments to skip"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get comments for a resource.
    """
    try:
        service = CollaborationService(db)
        comments = service.get_comments(
            resource_type=resource_type,
            resource_id=resource_id,
            user=current_user,
            limit=limit,
            offset=offset
        )

        # Get author names
        from models.user import User
        user_ids = [comment.author_id for comment in comments]
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {str(user.id): user.full_name for user in users}

        return [
            CommentResponse(
                id=str(comment.id),
                resource_type=comment.resource_type,
                resource_id=comment.resource_id,
                author_id=comment.author_id,
                content=comment.content,
                is_edited=comment.is_edited,
                parent_comment_id=comment.parent_comment_id,
                created_at=comment.created_at.isoformat(),
                author_name=user_map.get(comment.author_id, "Unknown User")
            )
            for comment in comments
        ]

    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comments: {str(e)}")


@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    limit: int = Query(50, description="Maximum number of notifications"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get notifications for the current user.
    """
    try:
        service = CollaborationService(db)
        notifications = service.get_notifications(
            user=current_user,
            unread_only=unread_only,
            limit=limit
        )

        return [
            NotificationResponse(
                id=str(notification.id),
                notification_type=notification.notification_type,
                title=notification.title,
                message=notification.message,
                resource_type=notification.resource_type,
                resource_id=notification.resource_id,
                is_read=notification.is_read,
                action_url=notification.action_url,
                priority=notification.priority,
                created_at=notification.created_at.isoformat()
            )
            for notification in notifications
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Mark a notification as read.
    """
    try:
        service = CollaborationService(db)
        service.mark_notification_read(current_user, notification_id)

        return {"message": "Notification marked as read"}

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")


@router.get("/activity", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    limit: int = Query(100, description="Maximum number of logs"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get activity logs accessible to the current user.
    """
    try:
        service = CollaborationService(db)
        logs = service.get_activity_logs(
            user=current_user,
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit
        )

        # Get user names
        user_ids = list(set(log.user_id for log in logs))
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {str(user.id): user.full_name for user in users}

        return [
            ActivityLogResponse(
                id=str(log.id),
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                description=log.description,
                success=log.success,
                created_at=log.created_at.isoformat(),
                user_name=user_map.get(log.user_id, "Unknown User")
            )
            for log in logs
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activity logs: {str(e)}")
