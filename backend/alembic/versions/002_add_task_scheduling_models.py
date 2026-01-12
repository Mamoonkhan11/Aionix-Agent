"""Add task scheduling models

Revision ID: 002
Revises: 001
Create Date: 2025-01-06 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create scheduled_tasks table
    op.create_table(
        'scheduled_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(length=100), nullable=False),
        sa.Column('frequency', sa.String(length=20), nullable=False),
        sa.Column('schedule_time', sa.Time(), nullable=True),
        sa.Column('schedule_days', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('task_config', sa.JSON(), nullable=False),
        sa.Column('agent_config', sa.JSON(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('is_shared', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('last_run', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create task_executions table
    op.create_table(
        'task_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_logs', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['scheduled_tasks.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('ix_scheduled_tasks_name', 'scheduled_tasks', ['name'], unique=False)
    op.create_index('ix_scheduled_tasks_task_type', 'scheduled_tasks', ['task_type'], unique=False)
    op.create_index('ix_scheduled_tasks_user_id', 'scheduled_tasks', ['user_id'], unique=False)
    op.create_index('ix_scheduled_tasks_is_active', 'scheduled_tasks', ['is_active'], unique=False)
    op.create_index('ix_scheduled_tasks_next_run', 'scheduled_tasks', ['next_run'], unique=False)
    op.create_index('ix_task_executions_task_id', 'task_executions', ['task_id'], unique=False)
    op.create_index('ix_task_executions_status', 'task_executions', ['status'], unique=False)
    op.create_index('ix_task_executions_celery_task_id', 'task_executions', ['celery_task_id'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop indexes
    op.drop_index('ix_task_executions_celery_task_id', table_name='task_executions')
    op.drop_index('ix_task_executions_status', table_name='task_executions')
    op.drop_index('ix_task_executions_task_id', table_name='task_executions')
    op.drop_index('ix_scheduled_tasks_next_run', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_is_active', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_user_id', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_task_type', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_name', 'scheduled_tasks')

    # Drop tables
    op.drop_table('task_executions')
    op.drop_table('scheduled_tasks')
