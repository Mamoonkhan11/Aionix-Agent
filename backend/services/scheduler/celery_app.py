"""
Celery application configuration for task scheduling.

This module sets up the Celery application with Redis as the broker and result backend,
providing the foundation for autonomous task execution.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Import settings
from core.config.settings import settings

# Create Celery app
celery_app = Celery(
    "aionix_scheduler",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["services.scheduler.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'retry_policy': {'timeout': 5.0}
    },

    # Beat scheduler settings
    beat_schedule={
        # Run every minute to check for due tasks
        'check-scheduled-tasks': {
            'task': 'services.scheduler.tasks.check_scheduled_tasks',
            'schedule': 60.0,  # Every 60 seconds
        },
    },
)

# Optional: Configure beat schedule dynamically if needed
celery_app.conf.beat_schedule_filename = os.path.join(
    os.path.dirname(__file__), 'celerybeat-schedule'
)

# Import tasks to register them with Celery
from . import tasks

if __name__ == "__main__":
    celery_app.start()
