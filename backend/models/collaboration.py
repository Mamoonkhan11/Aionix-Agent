"""
Collaboration models for multi-user features.

This module defines models for shared tasks, reports, access control,
and collaboration features in the AI system.
"""

from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import Base


class AccessLevel(str, Enum):
    """Access level enumeration for resource sharing."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class CollaborationType(str, Enum):
    """Type of collaboration resource."""

    TASK = "task"
    REPORT = "report"
    AGENT = "agent"
    WORKFLOW = "workflow"


class SharedResource(Base):
    """
    Model for resources that can be shared between users.

    Supports sharing of tasks, reports, agents, and workflows with
    granular access control.
    """

    __tablename__ = "shared_resources"

    # Resource identification
    resource_type: Mapped[CollaborationType] = Column(String(20), nullable=False, index=True)
    resource_id: Mapped[str] = Column(String(36), nullable=False, index=True)  # UUID of the actual resource

    # Sharing details
    owner_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    shared_with_user_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    access_level: Mapped[AccessLevel] = Column(String(10), nullable=False)

    # Sharing metadata
    shared_by: Mapped[str] = Column(UUID(as_uuid=True), nullable=False)
    share_message: Mapped[Optional[str]] = Column(Text)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], backref="shared_resources_owned")
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id], backref="shared_resources_received")

    @property
    def can_read(self) -> bool:
        """Check if the shared user can read the resource."""
        return self.access_level in [AccessLevel.READ, AccessLevel.WRITE, AccessLevel.ADMIN]

    @property
    def can_write(self) -> bool:
        """Check if the shared user can modify the resource."""
        return self.access_level in [AccessLevel.WRITE, AccessLevel.ADMIN]

    @property
    def can_admin(self) -> bool:
        """Check if the shared user has admin access."""
        return self.access_level == AccessLevel.ADMIN


class CollaborationSession(Base):
    """
    Model for real-time collaboration sessions.

    Tracks active collaboration sessions for shared workspaces.
    """

    __tablename__ = "collaboration_sessions"

    # Session details
    session_name: Mapped[str] = Column(String(255), nullable=False)
    session_type: Mapped[CollaborationType] = Column(String(20), nullable=False)
    resource_id: Mapped[Optional[str]] = Column(String(36))  # Associated resource if any

    # Participants
    created_by: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)

    # Session metadata
    max_participants: Mapped[int] = Column(Integer, default=10, nullable=False)
    session_data: Mapped[Optional[str]] = Column(Text)  # JSON string of session state

    # Relationships
    creator = relationship("User", backref="collaboration_sessions")

    # Participants relationship (many-to-many through session_participants)
    participants = relationship(
        "User",
        secondary="session_participants",
        backref="active_sessions"
    )


class SessionParticipant(Base):
    """
    Junction table for collaboration session participants.

    Links users to collaboration sessions with their roles.
    """

    __tablename__ = "session_participants"

    session_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("collaboration_sessions.id", ondelete="CASCADE"),
        primary_key=True
    )
    user_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    joined_at: Mapped[str] = Column(String(255), nullable=False)
    role: Mapped[str] = Column(String(50), default="participant", nullable=False)  # participant, moderator, observer
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)


class ActivityLog(Base):
    """
    Model for logging user activities and system events.

    Provides audit trails for security and compliance.
    """

    __tablename__ = "activity_logs"

    # Activity details
    user_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    action: Mapped[str] = Column(String(100), nullable=False, index=True)  # create, update, delete, share, etc.
    resource_type: Mapped[Optional[str]] = Column(String(50), index=True)  # task, report, agent, etc.
    resource_id: Mapped[Optional[str]] = Column(String(36), index=True)

    # Activity metadata
    description: Mapped[str] = Column(Text, nullable=False)
    ip_address: Mapped[Optional[str]] = Column(String(45))  # IPv4/IPv6
    user_agent: Mapped[Optional[str]] = Column(String(500))
    session_id: Mapped[Optional[str]] = Column(String(255))

    # Additional data
    extra_data: Mapped[Optional[str]] = Column(Text)  # JSON string of additional data
    success: Mapped[bool] = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", backref="activity_logs")


class Comment(Base):
    """
    Model for comments on shared resources.

    Enables discussion and feedback on collaborative content.
    """

    __tablename__ = "comments"

    # Comment details
    resource_type: Mapped[CollaborationType] = Column(String(20), nullable=False, index=True)
    resource_id: Mapped[str] = Column(String(36), nullable=False, index=True)

    # Author
    author_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Comment content
    content: Mapped[str] = Column(Text, nullable=False)
    is_edited: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    # Threading (for nested comments)
    parent_comment_id: Mapped[Optional[str]] = Column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE")
    )

    # Moderation
    is_deleted: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    deleted_by: Mapped[Optional[str]] = Column(UUID(as_uuid=True))
    deleted_at: Mapped[Optional[str]] = Column(String(255))

    # Relationships
    author = relationship("User", backref="comments")
    parent_comment = relationship("Comment", remote_side=[id], backref="replies")


class Notification(Base):
    """
    Model for user notifications.

    Handles notifications for shared resources, mentions, and system events.
    """

    __tablename__ = "notifications"

    # Notification details
    user_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    notification_type: Mapped[str] = Column(String(50), nullable=False, index=True)

    # Content
    title: Mapped[str] = Column(String(255), nullable=False)
    message: Mapped[str] = Column(Text, nullable=False)

    # Related resource
    resource_type: Mapped[Optional[str]] = Column(String(50))
    resource_id: Mapped[Optional[str]] = Column(String(36))

    # Status
    is_read: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[str]] = Column(String(255))

    # Action URL (for clickable notifications)
    action_url: Mapped[Optional[str]] = Column(String(500))

    # Priority
    priority: Mapped[str] = Column(String(20), default="normal", nullable=False)  # low, normal, high, urgent

    # Relationships
    user = relationship("User", backref="notifications")

    @property
    def is_unread(self) -> bool:
        """Check if notification is unread."""
        return not self.is_read


# Helper functions for access control
def check_resource_access(user_id: str, resource_type: CollaborationType, resource_id: str, required_access: AccessLevel) -> bool:
    """
    Check if a user has the required access level to a shared resource.

    This is a helper function that would typically be used in service layers.
    """
    from db.database import get_db
    from sqlalchemy.orm import Session

    db = next(get_db())

    # Check if user owns the resource
    if resource_type == CollaborationType.TASK:
        from models.task import ScheduledTask
        task = db.query(ScheduledTask).filter(
            ScheduledTask.id == resource_id,
            ScheduledTask.user_id == user_id
        ).first()
        if task:
            return True

    # Check shared access
    shared_resource = db.query(SharedResource).filter(
        SharedResource.resource_type == resource_type,
        SharedResource.resource_id == resource_id,
        SharedResource.shared_with_user_id == user_id,
        SharedResource.is_active == True
    ).first()

    if not shared_resource:
        return False

    # Check access level
    if required_access == AccessLevel.READ:
        return shared_resource.can_read
    elif required_access == AccessLevel.WRITE:
        return shared_resource.can_write
    elif required_access == AccessLevel.ADMIN:
        return shared_resource.can_admin

    return False


def log_activity(
    db: "Session",
    user_id: str,
    action: str,
    description: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    extra_data: Optional[dict] = None,
    success: bool = True
) -> ActivityLog:
    """
    Log a user activity for audit purposes.
    """
    from datetime import datetime

    activity = ActivityLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        extra_data=str(extra_data) if extra_data else None,
        success=success
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return activity
