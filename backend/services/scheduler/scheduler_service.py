"""
Scheduler service for managing autonomous tasks.

This module provides the business logic for creating, updating, and managing
scheduled tasks with proper validation and access control.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core.exceptions import NotFoundException, PermissionDeniedException
from models.task import ScheduledTask, TaskExecution, TaskStatus, TaskFrequency
from models.user import User, UserRole

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled tasks and their executions."""

    def __init__(self, db: Session):
        self.db = db

    def create_scheduled_task(
        self,
        user: User,
        name: str,
        description: Optional[str],
        task_type: str,
        frequency: TaskFrequency,
        task_config: Dict,
        agent_config: Optional[Dict] = None,
        schedule_time: Optional[str] = None,
        schedule_days: Optional[List[int]] = None,
        is_shared: bool = False
    ) -> ScheduledTask:
        """
        Create a new scheduled task.

        Args:
            user: The user creating the task
            name: Task name
            description: Task description
            task_type: Type of task (web_search, data_analysis, etc.)
            frequency: How often to run the task
            task_config: Task-specific configuration
            agent_config: Agent configuration for agent tasks
            schedule_time: Time of day for daily/weekly tasks (HH:MM format)
            schedule_days: Days of week for weekly tasks (0=Monday, 6=Sunday)
            is_shared: Whether the task can be viewed by other users

        Returns:
            Created ScheduledTask instance
        """
        # Validate task type
        valid_task_types = ["web_search", "data_analysis", "report_generation", "agent_interaction"]
        if task_type not in valid_task_types:
            raise ValueError(f"Invalid task type. Must be one of: {', '.join(valid_task_types)}")

        # Parse schedule time
        schedule_time_obj = None
        if schedule_time:
            try:
                schedule_time_obj = datetime.strptime(schedule_time, "%H:%M").time()
            except ValueError:
                raise ValueError("Invalid schedule_time format. Use HH:MM")

        # Serialize schedule days
        schedule_days_json = None
        if schedule_days:
            schedule_days_json = json.dumps(schedule_days)

        # Create task
        task = ScheduledTask(
            name=name,
            description=description,
            task_type=task_type,
            frequency=frequency,
            schedule_time=schedule_time_obj,
            schedule_days=schedule_days_json,
            task_config=task_config,
            agent_config=agent_config or {},
            user_id=str(user.id),
            created_by=str(user.id),
            is_shared=is_shared
        )

        # Calculate next run time
        task.next_run = task.calculate_next_run()

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Created scheduled task '{name}' for user {user.id}")
        return task

    def get_user_tasks(self, user: User, include_shared: bool = True) -> List[ScheduledTask]:
        """
        Get all tasks for a user.

        Args:
            user: The user requesting tasks
            include_shared: Whether to include shared tasks from other users

        Returns:
            List of ScheduledTask instances
        """
        query = self.db.query(ScheduledTask)

        if user.role == UserRole.ADMIN:
            # Admins can see all tasks
            pass
        else:
            # Regular users see their own tasks and shared tasks
            filters = [ScheduledTask.user_id == str(user.id)]
            if include_shared:
                filters.append(ScheduledTask.is_shared == True)
            query = query.filter(or_(*filters))

        return query.order_by(ScheduledTask.created_at.desc()).all()

    def get_task(self, task_id: str, user: User) -> ScheduledTask:
        """
        Get a specific task by ID with access control.

        Args:
            task_id: Task UUID
            user: User requesting the task

        Returns:
            ScheduledTask instance

        Raises:
            NotFoundException: If task doesn't exist or user doesn't have access
        """
        task = self.db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()

        if not task:
            raise NotFoundException(f"Task {task_id} not found")

        # Check access permissions
        if not self._can_access_task(task, user):
            raise PermissionDeniedException("You don't have permission to access this task")

        return task

    def update_task(
        self,
        task_id: str,
        user: User,
        **updates
    ) -> ScheduledTask:
        """
        Update a scheduled task.

        Args:
            task_id: Task UUID
            user: User making the update
            **updates: Fields to update

        Returns:
            Updated ScheduledTask instance
        """
        task = self.get_task(task_id, user)

        # Check if user can modify this task
        if not self._can_modify_task(task, user):
            raise PermissionDeniedException("You don't have permission to modify this task")

        # Handle special fields
        if 'schedule_time' in updates and updates['schedule_time']:
            try:
                updates['schedule_time'] = datetime.strptime(updates['schedule_time'], "%H:%M").time()
            except ValueError:
                raise ValueError("Invalid schedule_time format. Use HH:MM")

        if 'schedule_days' in updates and updates['schedule_days']:
            updates['schedule_days'] = json.dumps(updates['schedule_days'])

        # Update fields
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Recalculate next run time if schedule changed
        if any(key in updates for key in ['frequency', 'schedule_time', 'schedule_days']):
            task.next_run = task.calculate_next_run()

        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Updated scheduled task {task_id}")
        return task

    def delete_task(self, task_id: str, user: User) -> None:
        """
        Delete a scheduled task.

        Args:
            task_id: Task UUID
            user: User making the deletion
        """
        task = self.get_task(task_id, user)

        if not self._can_modify_task(task, user):
            raise PermissionDeniedException("You don't have permission to delete this task")

        self.db.delete(task)
        self.db.commit()

        logger.info(f"Deleted scheduled task {task_id}")

    def get_task_executions(
        self,
        task_id: str,
        user: User,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskExecution]:
        """
        Get execution history for a task.

        Args:
            task_id: Task UUID
            user: User requesting executions
            limit: Maximum number of executions to return
            offset: Number of executions to skip

        Returns:
            List of TaskExecution instances
        """
        # Verify user can access the task
        self.get_task(task_id, user)

        executions = self.db.query(TaskExecution).filter(
            TaskExecution.task_id == task_id
        ).order_by(TaskExecution.created_at.desc()).offset(offset).limit(limit).all()

        return executions

    def execute_task_now(self, task_id: str, user: User) -> TaskExecution:
        """
        Manually execute a task immediately.

        Args:
            task_id: Task UUID
            user: User requesting execution

        Returns:
            TaskExecution instance
        """
        task = self.get_task(task_id, user)

        # Import here to avoid circular imports
        from services.scheduler.tasks import execute_scheduled_task
        from services.scheduler.celery_app import celery_app

        # Queue the task for immediate execution
        result = execute_scheduled_task.delay(task_id)

        # Create execution record
        execution = TaskExecution(
            task_id=task_id,
            status=TaskStatus.PENDING,
            celery_task_id=result.id
        )

        self.db.add(execution)
        self.db.commit()

        logger.info(f"Queued task {task_id} for immediate execution")
        return execution

    def _can_access_task(self, task: ScheduledTask, user: User) -> bool:
        """Check if user can access a task."""
        if user.role == UserRole.ADMIN:
            return True
        if task.user_id == str(user.id):
            return True
        if task.is_shared:
            return True
        return False

    def _can_modify_task(self, task: ScheduledTask, user: User) -> bool:
        """Check if user can modify a task."""
        if user.role == UserRole.ADMIN:
            return True
        return task.user_id == str(user.id)
