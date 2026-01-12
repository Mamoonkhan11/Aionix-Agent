"""
Task scheduling models for autonomous AI operations.

This module defines models for scheduled tasks, task executions, and task definitions
that enable autonomous operation of AI agents.
"""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from .base import Base


class TaskStatus(str, Enum):
    """Status enumeration for task executions."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskFrequency(str, Enum):
    """Frequency enumeration for scheduled tasks."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    HOURLY = "hourly"
    MINUTELY = "minutely"


class ScheduledTask(Base):
    """
    Model for scheduled tasks that can be executed autonomously.

    Supports daily and weekly scheduling with configurable parameters.
    """

    __tablename__ = "scheduled_tasks"

    # Basic task information
    name: Mapped[str] = Column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(Text)
    task_type: Mapped[str] = Column(String(100), nullable=False, index=True)  # e.g., "web_search", "data_analysis"

    # Scheduling configuration
    frequency: Mapped[TaskFrequency] = Column(String(20), nullable=False)
    schedule_time: Mapped[Optional[str]] = Column(Time)  # For daily tasks
    schedule_days: Mapped[Optional[str]] = Column(String(50))  # JSON array of weekdays for weekly tasks
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)

    # Task parameters and configuration
    task_config: Mapped[Dict[str, Any]] = Column(JSON, default=dict, nullable=False)
    agent_config: Mapped[Dict[str, Any]] = Column(JSON, default=dict, nullable=False)

    # User and access control
    user_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    is_shared: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    # Metadata
    created_by: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    last_run: Mapped[Optional[DateTime]] = Column(DateTime(timezone=True))
    next_run: Mapped[Optional[DateTime]] = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", backref="scheduled_tasks")
    executions = relationship("TaskExecution", backref="task", cascade="all, delete-orphan")

    @property
    def is_due(self) -> bool:
        """Check if the task is due for execution."""
        if not self.is_active or not self.next_run:
            return False
        return self.next_run <= func.now()

    def calculate_next_run(self) -> Optional[DateTime]:
        """Calculate the next execution time based on frequency."""
        from datetime import datetime, timedelta
        import json

        now = datetime.now()

        if self.frequency == TaskFrequency.DAILY:
            if self.schedule_time:
                # Parse time and combine with today's date
                schedule_hour = self.schedule_time.hour
                schedule_minute = self.schedule_time.minute

                next_run = now.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)

                # If the time has already passed today, schedule for tomorrow
                if next_run <= now:
                    next_run = next_run + timedelta(days=1)

                return next_run

        elif self.frequency == TaskFrequency.WEEKLY:
            if self.schedule_days and self.schedule_time:
                try:
                    days = json.loads(self.schedule_days)
                    schedule_hour = self.schedule_time.hour
                    schedule_minute = self.schedule_time.minute

                    # Find next occurrence in the week
                    current_weekday = now.weekday()  # Monday = 0

                    for day in sorted(days):
                        if day > current_weekday:
                            # Next occurrence this week
                            days_ahead = day - current_weekday
                            next_run = now + timedelta(days=days_ahead)
                            next_run = next_run.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
                            return next_run
                        elif day == current_weekday:
                            # Today - check if time has passed
                            next_run = now.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
                            if next_run > now:
                                return next_run

                    # Next week - start from first day
                    days_ahead = 7 - current_weekday + sorted(days)[0]
                    next_run = now + timedelta(days=days_ahead)
                    next_run = next_run.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
                    return next_run

                except (json.JSONDecodeError, ValueError):
                    return None

        elif self.frequency == TaskFrequency.HOURLY:
            # Run at the next hour boundary
            next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            return next_run

        elif self.frequency == TaskFrequency.MINUTELY:
            # Run at the next minute boundary
            next_run = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            return next_run

        return None


class TaskExecution(Base):
    """
    Model for tracking task execution history and results.

    Provides logging and monitoring capabilities for scheduled tasks.
    """

    __tablename__ = "task_executions"

    # Task reference
    task_id: Mapped[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("scheduled_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Execution details
    status: Mapped[TaskStatus] = Column(String(20), nullable=False, default=TaskStatus.PENDING)
    started_at: Mapped[Optional[DateTime]] = Column(DateTime(timezone=True))
    completed_at: Mapped[Optional[DateTime]] = Column(DateTime(timezone=True))

    # Results and logging
    result_data: Mapped[Optional[Dict[str, Any]]] = Column(JSON)
    error_message: Mapped[Optional[str]] = Column(Text)
    execution_logs: Mapped[Optional[str]] = Column(Text)

    # Performance metrics
    duration_seconds: Mapped[Optional[float]] = Column(Float)

    # Celery task ID for tracking
    celery_task_id: Mapped[Optional[str]] = Column(String(255), index=True)

    @property
    def duration(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_successful(self) -> bool:
        """Check if the execution was successful."""
        return self.status == TaskStatus.COMPLETED

    def mark_started(self) -> None:
        """Mark the execution as started."""
        from datetime import datetime
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, result_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark the execution as completed."""
        from datetime import datetime
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result_data = result_data or {}
        self.duration_seconds = self.duration

    def mark_failed(self, error_message: str, execution_logs: Optional[str] = None) -> None:
        """Mark the execution as failed."""
        from datetime import datetime
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
        self.execution_logs = execution_logs
        self.duration_seconds = self.duration
