"""
Background Task Runner for AI Processing.

Provides async background task processing with status tracking,
retry logic, and idempotency.
"""

import asyncio
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class Task:
    """Represents a background task."""

    def __init__(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: Dict = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        Initialize task.

        Args:
            task_id: Unique task identifier
            func: Async function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
        """
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.status = TaskStatus.PENDING
        self.result: Any = None
        self.error: Optional[Exception] = None
        self.retry_count = 0
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    async def execute(self) -> Any:
        """Execute the task with retry logic."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

        while self.retry_count <= self.max_retries:
            try:
                logger.info(f"Executing task {self.task_id} (attempt {self.retry_count + 1})")
                self.result = await self.func(*self.args, **self.kwargs)
                self.status = TaskStatus.SUCCESS
                self.completed_at = datetime.utcnow()
                logger.info(f"Task {self.task_id} completed successfully")
                return self.result

            except Exception as e:
                self.error = e
                self.retry_count += 1

                if self.retry_count > self.max_retries:
                    self.status = TaskStatus.FAILED
                    self.completed_at = datetime.utcnow()
                    logger.error(f"Task {self.task_id} failed after {self.max_retries} retries: {e}")
                    raise
                else:
                    self.status = TaskStatus.RETRYING
                    logger.warning(
                        f"Task {self.task_id} failed, retrying in {self.retry_delay}s "
                        f"(attempt {self.retry_count}/{self.max_retries})"
                    )
                    await asyncio.sleep(self.retry_delay)

    def to_dict(self) -> Dict:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": str(self.error) if self.error else None,
        }


class TaskRunner:
    """
    Manages background task execution with status tracking.
    """

    def __init__(self):
        """Initialize task runner."""
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def submit_task(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Dict = None,
        task_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
        run_async: bool = True,
    ) -> str:
        """
        Submit a task for execution.

        Args:
            func: Async function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            task_id: Optional task ID (generated if not provided)
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries
            run_async: Whether to run asynchronously

        Returns:
            str: Task ID
        """
        if task_id is None:
            task_id = str(uuid4())

        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        self.tasks[task_id] = task

        if run_async:
            # Run task in background
            asyncio_task = asyncio.create_task(self._run_task(task))
            self.running_tasks[task_id] = asyncio_task
        else:
            # Run task synchronously
            await task.execute()

        return task_id

    async def _run_task(self, task: Task):
        """Run a task and handle cleanup."""
        try:
            await task.execute()
        except Exception as e:
            logger.error(f"Task {task.task_id} execution failed: {e}")
        finally:
            # Remove from running tasks
            self.running_tasks.pop(task.task_id, None)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Get task status.

        Args:
            task_id: Task ID

        Returns:
            Dict: Task status information
        """
        task = self.tasks.get(task_id)
        if task:
            return task.to_dict()
        return None

    def get_task_result(self, task_id: str) -> Any:
        """
        Get task result.

        Args:
            task_id: Task ID

        Returns:
            Any: Task result or None
        """
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.SUCCESS:
            return task.result
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task ID

        Returns:
            bool: True if cancelled
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.RUNNING:
            asyncio_task = self.running_tasks.get(task_id)
            if asyncio_task:
                asyncio_task.cancel()
                task.status = TaskStatus.CANCELLED
                return True

        return False

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List[Dict]: List of task information
        """
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [task.to_dict() for task in tasks]


# Global task runner instance
task_runner = TaskRunner()
