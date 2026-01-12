"""
Celery tasks for autonomous AI operations.

This module defines the actual tasks that are executed by Celery workers,
including scheduled task checking, web search, data processing, and more.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ai_engine.orchestration.task_runner import TaskRunner
from core.config.settings import settings
from db.database import get_db
from models.task import ScheduledTask, TaskExecution, TaskStatus, TaskFrequency
from services.scheduler.celery_app import celery_app
from services.web_search.search_agent import WebSearchAgent

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="services.scheduler.tasks.check_scheduled_tasks")
def check_scheduled_tasks(self):
    """
    Periodic task to check for and execute due scheduled tasks.

    This task runs every minute and identifies tasks that are due for execution,
    then queues them for processing.
    """
    try:
        db = next(get_db())

        # Find tasks that are due for execution
        due_tasks = db.query(ScheduledTask).filter(
            and_(
                ScheduledTask.is_active == True,
                ScheduledTask.next_run <= datetime.now()
            )
        ).all()

        for task in due_tasks:
            # Queue the task for execution
            execute_scheduled_task.delay(str(task.id))

            # Update next run time
            task.last_run = datetime.now()
            task.next_run = task.calculate_next_run()

        db.commit()
        logger.info(f"Checked scheduled tasks, found {len(due_tasks)} due tasks")

    except Exception as e:
        logger.error(f"Error checking scheduled tasks: {str(e)}")
        raise self.retry(countdown=60, max_retries=3)


@celery_app.task(bind=True, name="services.scheduler.tasks.execute_scheduled_task")
def execute_scheduled_task(self, task_id: str):
    """
    Execute a specific scheduled task.

    Args:
        task_id: UUID of the scheduled task to execute
    """
    execution = None
    db = None

    try:
        db = next(get_db())

        # Get the task
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            logger.error(f"Scheduled task {task_id} not found")
            return

        # Create execution record
        execution = TaskExecution(
            task_id=task_id,
            celery_task_id=self.request.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        db.add(execution)
        db.commit()

        # Execute based on task type
        if task.task_type == "web_search":
            result = execute_web_search_task(task, execution)
        elif task.task_type == "data_analysis":
            result = execute_data_analysis_task(task, execution)
        elif task.task_type == "report_generation":
            result = execute_report_generation_task(task, execution)
        elif task.task_type == "agent_interaction":
            result = execute_agent_interaction_task(task, execution)
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

        # Mark as completed
        execution.mark_completed(result)
        db.commit()

        logger.info(f"Successfully executed scheduled task {task_id} ({task.task_type})")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error executing scheduled task {task_id}: {error_msg}")

        if execution and db:
            execution.mark_failed(error_msg)
            db.commit()

        raise self.retry(countdown=300, max_retries=2)  # Retry after 5 minutes


@celery_app.task(bind=True, name="services.scheduler.tasks.execute_web_search_task")
def execute_web_search_task(task: ScheduledTask, execution: TaskExecution) -> Dict[str, Any]:
    """
    Execute a web search task.

    Args:
        task: The scheduled task configuration
        execution: The execution record for logging

    Returns:
        Dict containing search results and metadata
    """
    try:
        # Initialize web search agent
        search_agent = WebSearchAgent()

        # Get search configuration from task
        search_config = task.task_config
        query = search_config.get("query", "")
        max_results = search_config.get("max_results", 10)
        search_type = search_config.get("search_type", "general")

        if not query:
            raise ValueError("Search query is required for web search tasks")

        # Execute search
        results = search_agent.search_and_process(query, max_results, search_type)

        # Return structured results
        return {
            "search_query": query,
            "results_count": len(results),
            "search_type": search_type,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in web search task: {str(e)}")
        raise


@celery_app.task(bind=True, name="services.scheduler.tasks.execute_data_analysis_task")
def execute_data_analysis_task(task: ScheduledTask, execution: TaskExecution) -> Dict[str, Any]:
    """
    Execute a data analysis task.

    Args:
        task: The scheduled task configuration
        execution: The execution record for logging

    Returns:
        Dict containing analysis results
    """
    try:
        # Initialize task runner for AI operations
        task_runner = TaskRunner()

        # Get analysis configuration
        analysis_config = task.task_config
        data_source = analysis_config.get("data_source", "")
        analysis_type = analysis_config.get("analysis_type", "general")
        parameters = analysis_config.get("parameters", {})

        # Execute analysis
        result = task_runner.run_analysis_task(data_source, analysis_type, parameters)

        return {
            "data_source": data_source,
            "analysis_type": analysis_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in data analysis task: {str(e)}")
        raise


@celery_app.task(bind=True, name="services.scheduler.tasks.execute_report_generation_task")
def execute_report_generation_task(task: ScheduledTask, execution: TaskExecution) -> Dict[str, Any]:
    """
    Execute a report generation task.

    Args:
        task: The scheduled task configuration
        execution: The execution record for logging

    Returns:
        Dict containing report generation results
    """
    try:
        # Initialize task runner
        task_runner = TaskRunner()

        # Get report configuration
        report_config = task.task_config
        report_type = report_config.get("report_type", "summary")
        data_sources = report_config.get("data_sources", [])
        parameters = report_config.get("parameters", {})

        # Generate report
        report = task_runner.generate_report(report_type, data_sources, parameters)

        return {
            "report_type": report_type,
            "data_sources": data_sources,
            "report": report,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in report generation task: {str(e)}")
        raise


@celery_app.task(bind=True, name="services.scheduler.tasks.execute_agent_interaction_task")
def execute_agent_interaction_task(task: ScheduledTask, execution: TaskExecution) -> Dict[str, Any]:
    """
    Execute an agent interaction task.

    Args:
        task: The scheduled task configuration
        execution: The execution record for logging

    Returns:
        Dict containing agent interaction results
    """
    try:
        # Get agent configuration
        agent_config = task.agent_config
        agent_type = agent_config.get("agent_type", "")
        agent_parameters = agent_config.get("parameters", {})
        interaction_type = agent_config.get("interaction_type", "query")

        # This would integrate with the pluggable agent framework
        # For now, return placeholder result
        result = {
            "agent_type": agent_type,
            "interaction_type": interaction_type,
            "parameters": agent_parameters,
            "status": "executed",
            "timestamp": datetime.now().isoformat()
        }

        return result

    except Exception as e:
        logger.error(f"Error in agent interaction task: {str(e)}")
        raise


# Utility tasks for maintenance and monitoring
@celery_app.task(bind=True, name="services.scheduler.tasks.cleanup_old_executions")
def cleanup_old_executions(self, days_to_keep: int = 30):
    """
    Clean up old task execution records.

    Args:
        days_to_keep: Number of days of execution history to keep
    """
    try:
        db = next(get_db())

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Delete old executions
        deleted_count = db.query(TaskExecution).filter(
            TaskExecution.created_at < cutoff_date
        ).delete()

        db.commit()

        logger.info(f"Cleaned up {deleted_count} old task executions")

    except Exception as e:
        logger.error(f"Error cleaning up old executions: {str(e)}")
        raise


@celery_app.task(bind=True, name="services.scheduler.tasks.update_task_schedules")
def update_task_schedules(self):
    """
    Update next run times for all active scheduled tasks.

    This task ensures that task schedules remain accurate and handles
    any missed executions.
    """
    try:
        db = next(get_db())

        # Update next run times for all active tasks
        tasks = db.query(ScheduledTask).filter(ScheduledTask.is_active == True).all()

        for task in tasks:
            if not task.next_run or task.next_run <= datetime.now():
                task.next_run = task.calculate_next_run()

        db.commit()

        logger.info(f"Updated schedules for {len(tasks)} active tasks")

    except Exception as e:
        logger.error(f"Error updating task schedules: {str(e)}")
        raise
