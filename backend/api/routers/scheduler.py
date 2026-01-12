"""
Scheduler API router for managing autonomous tasks.

This module provides REST endpoints for creating, managing, and monitoring
scheduled tasks in the autonomous AI system.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from core.exceptions import NotFoundException, PermissionDeniedException
from models.task import ScheduledTask, TaskExecution, TaskFrequency
from models.user import User
from services.scheduler.scheduler_service import SchedulerService

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# Pydantic models for API
class TaskConfig(BaseModel):
    """Configuration for task execution."""
    query: Optional[str] = None
    max_results: Optional[int] = 10
    search_type: Optional[str] = "general"
    data_source: Optional[str] = None
    analysis_type: Optional[str] = "general"
    report_type: Optional[str] = "summary"
    data_sources: Optional[List[str]] = None
    parameters: Optional[dict] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """Configuration for agent interaction."""
    agent_type: Optional[str] = None
    interaction_type: Optional[str] = "query"
    parameters: Optional[dict] = Field(default_factory=dict)


class ScheduledTaskCreate(BaseModel):
    """Request model for creating a scheduled task."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: str = Field(..., description="Type of task: web_search, data_analysis, report_generation, agent_interaction")
    frequency: TaskFrequency
    task_config: TaskConfig
    agent_config: Optional[AgentConfig] = None
    schedule_time: Optional[str] = Field(None, description="Time in HH:MM format for daily/weekly tasks")
    schedule_days: Optional[List[int]] = Field(None, description="Days of week (0=Monday, 6=Sunday) for weekly tasks")
    is_shared: bool = False


class ScheduledTaskUpdate(BaseModel):
    """Request model for updating a scheduled task."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_config: Optional[TaskConfig] = None
    agent_config: Optional[AgentConfig] = None
    schedule_time: Optional[str] = None
    schedule_days: Optional[List[int]] = None
    is_active: Optional[bool] = None
    is_shared: Optional[bool] = None


class ScheduledTaskResponse(BaseModel):
    """Response model for scheduled task."""
    id: str
    name: str
    description: Optional[str]
    task_type: str
    frequency: TaskFrequency
    schedule_time: Optional[str]
    schedule_days: Optional[List[int]]
    is_active: bool
    is_shared: bool
    task_config: dict
    agent_config: dict
    user_id: str
    created_by: str
    last_run: Optional[str]
    next_run: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TaskExecutionResponse(BaseModel):
    """Response model for task execution."""
    id: str
    task_id: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result_data: Optional[dict]
    error_message: Optional[str]
    execution_logs: Optional[str]
    duration_seconds: Optional[float]
    celery_task_id: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# API Endpoints
@router.post("/tasks", response_model=ScheduledTaskResponse)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new scheduled task.

    Tasks can be configured to run daily, weekly, or at custom intervals.
    """
    try:
        scheduler_service = SchedulerService(db)

        task = scheduler_service.create_scheduled_task(
            user=current_user,
            name=task_data.name,
            description=task_data.description,
            task_type=task_data.task_type,
            frequency=task_data.frequency,
            task_config=task_data.task_config.dict(),
            agent_config=task_data.agent_config.dict() if task_data.agent_config else None,
            schedule_time=task_data.schedule_time,
            schedule_days=task_data.schedule_days,
            is_shared=task_data.is_shared
        )

        return ScheduledTaskResponse.from_orm(task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/tasks", response_model=List[ScheduledTaskResponse])
async def get_scheduled_tasks(
    include_shared: bool = Query(True, description="Include shared tasks from other users"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all scheduled tasks accessible to the current user.

    Returns both owned tasks and shared tasks from other users.
    """
    try:
        scheduler_service = SchedulerService(db)
        tasks = scheduler_service.get_user_tasks(current_user, include_shared)

        return [ScheduledTaskResponse.from_orm(task) for task in tasks]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tasks: {str(e)}")


@router.get("/tasks/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific scheduled task by ID.
    """
    try:
        scheduler_service = SchedulerService(db)
        task = scheduler_service.get_task(task_id, current_user)

        return ScheduledTaskResponse.from_orm(task)

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task: {str(e)}")


@router.put("/tasks/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: str,
    task_data: ScheduledTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing scheduled task.
    """
    try:
        scheduler_service = SchedulerService(db)

        update_data = task_data.dict(exclude_unset=True)
        if 'task_config' in update_data:
            update_data['task_config'] = update_data['task_config']
        if 'agent_config' in update_data:
            update_data['agent_config'] = update_data['agent_config']

        task = scheduler_service.update_task(task_id, current_user, **update_data)

        return ScheduledTaskResponse.from_orm(task)

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.delete("/tasks/{task_id}")
async def delete_scheduled_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a scheduled task.
    """
    try:
        scheduler_service = SchedulerService(db)
        scheduler_service.delete_task(task_id, current_user)

        return {"message": "Task deleted successfully"}

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")


@router.post("/tasks/{task_id}/execute")
async def execute_task_now(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute a scheduled task immediately.
    """
    try:
        scheduler_service = SchedulerService(db)
        execution = scheduler_service.execute_task_now(task_id, current_user)

        return {
            "message": "Task execution queued",
            "execution_id": str(execution.id),
            "celery_task_id": execution.celery_task_id
        }

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@router.get("/tasks/{task_id}/executions", response_model=List[TaskExecutionResponse])
async def get_task_executions(
    task_id: str,
    limit: int = Query(50, description="Maximum number of executions to return"),
    offset: int = Query(0, description="Number of executions to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get execution history for a specific task.
    """
    try:
        scheduler_service = SchedulerService(db)
        executions = scheduler_service.get_task_executions(task_id, current_user, limit, offset)

        return [TaskExecutionResponse.from_orm(execution) for execution in executions]

    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve executions: {str(e)}")


@router.get("/executions/{execution_id}", response_model=TaskExecutionResponse)
async def get_task_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific task execution.
    """
    try:
        # Get execution and verify access through associated task
        execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Verify user can access the associated task
        scheduler_service = SchedulerService(db)
        scheduler_service.get_task(str(execution.task_id), current_user)

        return TaskExecutionResponse.from_orm(execution)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve execution: {str(e)}")
