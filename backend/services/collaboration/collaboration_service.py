"""
Collaboration service for multi-user features.

This module provides business logic for shared resources, access control,
real-time collaboration, and activity logging.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core.exceptions import NotFoundException, PermissionDeniedException
from models.collaboration import (
    AccessLevel,
    ActivityLog,
    CollaborationSession,
    CollaborationType,
    Comment,
    Notification,
    SessionParticipant,
    SharedResource,
    check_resource_access,
    log_activity
)
from models.user import User, UserRole


class CollaborationService:
    """Service for managing collaborative features and access control."""

    def __init__(self, db: Session):
        self.db = db

    def share_resource(
        self,
        owner: User,
        resource_type: CollaborationType,
        resource_id: str,
        shared_with_user_id: str,
        access_level: AccessLevel,
        share_message: Optional[str] = None
    ) -> SharedResource:
        """
        Share a resource with another user.

        Args:
            owner: User sharing the resource
            resource_type: Type of resource being shared
            resource_id: ID of the resource
            shared_with_user_id: User to share with
            access_level: Level of access to grant
            share_message: Optional message to include

        Returns:
            SharedResource instance
        """
        # Verify the target user exists
        target_user = self.db.query(User).filter(User.id == shared_with_user_id).first()
        if not target_user:
            raise NotFoundException("Target user not found")

        # Check if owner has permission to share this resource
        if not self._can_share_resource(owner, resource_type, resource_id):
            raise PermissionDeniedException("You don't have permission to share this resource")

        # Check if already shared
        existing_share = self.db.query(SharedResource).filter(
            and_(
                SharedResource.resource_type == resource_type,
                SharedResource.resource_id == resource_id,
                SharedResource.shared_with_user_id == shared_with_user_id,
                SharedResource.is_active == True
            )
        ).first()

        if existing_share:
            # Update existing share
            existing_share.access_level = access_level
            existing_share.share_message = share_message
            self.db.commit()
            self.db.refresh(existing_share)

            # Log activity
            log_activity(
                self.db, str(owner.id), "update_share",
                f"Updated sharing permissions for {resource_type} {resource_id}",
                resource_type.value, resource_id,
                {"shared_with": shared_with_user_id, "access_level": access_level.value}
            )

            return existing_share

        # Create new share
        share = SharedResource(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=str(owner.id),
            shared_with_user_id=shared_with_user_id,
            access_level=access_level,
            shared_by=str(owner.id),
            share_message=share_message
        )

        self.db.add(share)
        self.db.commit()
        self.db.refresh(share)

        # Create notification for the shared user
        self._create_notification(
            user_id=shared_with_user_id,
            notification_type="resource_shared",
            title=f"Resource shared with you",
            message=f"{owner.full_name} shared a {resource_type.value} with you",
            resource_type=resource_type.value,
            resource_id=resource_id,
            action_url=f"/{resource_type.value}s/{resource_id}"
        )

        # Log activity
        log_activity(
            self.db, str(owner.id), "share_resource",
            f"Shared {resource_type} {resource_id} with user {shared_with_user_id}",
            resource_type.value, resource_id,
            {"shared_with": shared_with_user_id, "access_level": access_level.value}
        )

        return share

    def get_shared_resources(self, user: User) -> List[SharedResource]:
        """
        Get all resources shared with a user.

        Args:
            user: User to get shared resources for

        Returns:
            List of SharedResource instances
        """
        query = self.db.query(SharedResource).filter(
            and_(
                SharedResource.shared_with_user_id == str(user.id),
                SharedResource.is_active == True
            )
        )

        return query.order_by(SharedResource.created_at.desc()).all()

    def revoke_share(self, owner: User, share_id: str) -> None:
        """
        Revoke a resource share.

        Args:
            owner: User revoking the share
            share_id: ID of the share to revoke
        """
        share = self.db.query(SharedResource).filter(SharedResource.id == share_id).first()

        if not share:
            raise NotFoundException("Share not found")

        if share.owner_id != str(owner.id):
            raise PermissionDeniedException("You can only revoke your own shares")

        share.is_active = False
        self.db.commit()

        # Log activity
        log_activity(
            self.db, str(owner.id), "revoke_share",
            f"Revoked sharing of {share.resource_type} {share.resource_id}",
            share.resource_type.value, share.resource_id,
            {"revoked_from": share.shared_with_user_id}
        )

    def create_collaboration_session(
        self,
        creator: User,
        session_name: str,
        session_type: CollaborationType,
        resource_id: Optional[str] = None,
        max_participants: int = 10
    ) -> CollaborationSession:
        """
        Create a new collaboration session.

        Args:
            creator: User creating the session
            session_name: Name of the session
            session_type: Type of collaboration
            resource_id: Optional associated resource
            max_participants: Maximum number of participants

        Returns:
            CollaborationSession instance
        """
        session = CollaborationSession(
            session_name=session_name,
            session_type=session_type,
            resource_id=resource_id,
            created_by=str(creator.id),
            max_participants=max_participants
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # Add creator as participant
        self._add_session_participant(session.id, creator.id, "moderator")

        # Log activity
        log_activity(
            self.db, str(creator.id), "create_session",
            f"Created collaboration session: {session_name}",
            "session", str(session.id)
        )

        return session

    def join_collaboration_session(self, user: User, session_id: str) -> SessionParticipant:
        """
        Join a collaboration session.

        Args:
            user: User joining the session
            session_id: ID of the session to join

        Returns:
            SessionParticipant instance
        """
        session = self.db.query(CollaborationSession).filter(
            and_(
                CollaborationSession.id == session_id,
                CollaborationSession.is_active == True
            )
        ).first()

        if not session:
            raise NotFoundException("Collaboration session not found")

        # Check participant limit
        participant_count = self.db.query(SessionParticipant).filter(
            and_(
                SessionParticipant.session_id == session_id,
                SessionParticipant.is_active == True
            )
        ).count()

        if participant_count >= session.max_participants:
            raise PermissionDeniedException("Session is full")

        # Check if already a participant
        existing_participant = self.db.query(SessionParticipant).filter(
            and_(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == str(user.id)
            )
        ).first()

        if existing_participant:
            if existing_participant.is_active:
                raise PermissionDeniedException("Already a participant in this session")
            else:
                # Reactivate participant
                existing_participant.is_active = True
                self.db.commit()
                return existing_participant

        # Add as new participant
        participant = self._add_session_participant(session_id, str(user.id), "participant")

        # Log activity
        log_activity(
            self.db, str(user.id), "join_session",
            f"Joined collaboration session: {session.session_name}",
            "session", session_id
        )

        return participant

    def leave_collaboration_session(self, user: User, session_id: str) -> None:
        """
        Leave a collaboration session.

        Args:
            user: User leaving the session
            session_id: ID of the session to leave
        """
        participant = self.db.query(SessionParticipant).filter(
            and_(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == str(user.id),
                SessionParticipant.is_active == True
            )
        ).first()

        if not participant:
            raise NotFoundException("Not a participant in this session")

        participant.is_active = False
        self.db.commit()

        # Log activity
        log_activity(
            self.db, str(user.id), "leave_session",
            "Left collaboration session",
            "session", session_id
        )

    def add_comment(
        self,
        user: User,
        resource_type: CollaborationType,
        resource_id: str,
        content: str,
        parent_comment_id: Optional[str] = None
    ) -> Comment:
        """
        Add a comment to a resource.

        Args:
            user: User adding the comment
            resource_type: Type of resource being commented on
            resource_id: ID of the resource
            content: Comment content
            parent_comment_id: Optional parent comment for threading

        Returns:
            Comment instance
        """
        # Check access to the resource
        if not check_resource_access(str(user.id), resource_type, resource_id, AccessLevel.READ):
            raise PermissionDeniedException("You don't have access to comment on this resource")

        comment = Comment(
            resource_type=resource_type,
            resource_id=resource_id,
            author_id=str(user.id),
            content=content,
            parent_comment_id=parent_comment_id
        )

        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)

        # Log activity
        log_activity(
            self.db, str(user.id), "add_comment",
            f"Added comment to {resource_type} {resource_id}",
            resource_type.value, resource_id
        )

        return comment

    def get_comments(
        self,
        resource_type: CollaborationType,
        resource_id: str,
        user: User,
        limit: int = 50,
        offset: int = 0
    ) -> List[Comment]:
        """
        Get comments for a resource.

        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            user: User requesting comments
            limit: Maximum number of comments
            offset: Number of comments to skip

        Returns:
            List of Comment instances
        """
        # Check access
        if not check_resource_access(str(user.id), resource_type, resource_id, AccessLevel.READ):
            raise PermissionDeniedException("You don't have access to view comments on this resource")

        comments = self.db.query(Comment).filter(
            and_(
                Comment.resource_type == resource_type,
                Comment.resource_id == resource_id,
                Comment.is_deleted == False
            )
        ).order_by(Comment.created_at.desc()).offset(offset).limit(limit).all()

        return comments

    def get_notifications(self, user: User, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        """
        Get notifications for a user.

        Args:
            user: User to get notifications for
            unread_only: Whether to return only unread notifications
            limit: Maximum number of notifications

        Returns:
            List of Notification instances
        """
        query = self.db.query(Notification).filter(Notification.user_id == str(user.id))

        if unread_only:
            query = query.filter(Notification.is_read == False)

        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def mark_notification_read(self, user: User, notification_id: str) -> None:
        """
        Mark a notification as read.

        Args:
            user: User marking the notification
            notification_id: ID of the notification
        """
        notification = self.db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == str(user.id)
            )
        ).first()

        if not notification:
            raise NotFoundException("Notification not found")

        notification.is_read = True
        notification.read_at = datetime.now().isoformat()
        self.db.commit()

    def get_activity_logs(
        self,
        user: User,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ActivityLog]:
        """
        Get activity logs, filtered by user permissions.

        Args:
            user: User requesting logs
            resource_type: Optional resource type filter
            resource_id: Optional resource ID filter
            limit: Maximum number of logs

        Returns:
            List of ActivityLog instances
        """
        query = self.db.query(ActivityLog)

        # Filter by user permissions
        if user.role != UserRole.ADMIN:
            # Non-admins can only see their own activities and activities on resources they can access
            user_activities = [ActivityLog.user_id == str(user.id)]

            # Add activities on accessible resources
            if resource_type and resource_id:
                if check_resource_access(str(user.id), CollaborationType(resource_type), resource_id, AccessLevel.READ):
                    user_activities.append(
                        and_(
                            ActivityLog.resource_type == resource_type,
                            ActivityLog.resource_id == resource_id
                        )
                    )

            query = query.filter(or_(*user_activities))

        if resource_type:
            query = query.filter(ActivityLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(ActivityLog.resource_id == resource_id)

        return query.order_by(ActivityLog.created_at.desc()).limit(limit).all()

    def _can_share_resource(self, user: User, resource_type: CollaborationType, resource_id: str) -> bool:
        """Check if user can share a resource."""
        if user.role == UserRole.ADMIN:
            return True

        # Check ownership or admin access
        return check_resource_access(str(user.id), resource_type, resource_id, AccessLevel.ADMIN)

    def _add_session_participant(self, session_id: str, user_id: str, role: str) -> SessionParticipant:
        """Add a participant to a session."""
        participant = SessionParticipant(
            session_id=str(session_id),
            user_id=user_id,
            joined_at=datetime.now().isoformat(),
            role=role,
            is_active=True
        )

        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)

        return participant

    def _create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action_url: Optional[str] = None,
        priority: str = "normal"
    ) -> Notification:
        """Create a notification for a user."""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            action_url=action_url,
            priority=priority
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        return notification
