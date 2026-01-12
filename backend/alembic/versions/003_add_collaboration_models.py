"""Add collaboration models

Revision ID: 003
Revises: 002
Create Date: 2025-01-06 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create shared_resources table
    op.create_table(
        'shared_resources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resource_type', sa.String(length=20), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('shared_with_user_id', sa.String(length=36), nullable=False),
        sa.Column('access_level', sa.String(length=10), nullable=False),
        sa.Column('shared_by', sa.String(length=36), nullable=False),
        sa.Column('share_message', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_with_user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create collaboration_sessions table
    op.create_table(
        'collaboration_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_name', sa.String(length=255), nullable=False),
        sa.Column('session_type', sa.String(length=20), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('max_participants', sa.Integer(), nullable=False),
        sa.Column('session_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE')
    )

    # Create session_participants table
    op.create_table(
        'session_participants',
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('joined_at', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('session_id', 'user_id'),
        sa.ForeignKeyConstraint(['session_id'], ['collaboration_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create comments table
    op.create_table(
        'comments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resource_type', sa.String(length=20), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=False),
        sa.Column('author_id', sa.String(length=36), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_edited', sa.Boolean(), nullable=False),
        sa.Column('parent_comment_id', sa.String(length=36), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_by', sa.String(length=36), nullable=True),
        sa.Column('deleted_at', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_comment_id'], ['comments.id'], ondelete='CASCADE')
    )

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('read_at', sa.String(length=255), nullable=True),
        sa.Column('action_url', sa.String(length=500), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('ix_shared_resources_resource_type', 'shared_resources', ['resource_type'], unique=False)
    op.create_index('ix_shared_resources_resource_id', 'shared_resources', ['resource_id'], unique=False)
    op.create_index('ix_shared_resources_owner_id', 'shared_resources', ['owner_id'], unique=False)
    op.create_index('ix_shared_resources_shared_with_user_id', 'shared_resources', ['shared_with_user_id'], unique=False)
    op.create_index('ix_collaboration_sessions_created_by', 'collaboration_sessions', ['created_by'], unique=False)
    op.create_index('ix_activity_logs_user_id', 'activity_logs', ['user_id'], unique=False)
    op.create_index('ix_activity_logs_action', 'activity_logs', ['action'], unique=False)
    op.create_index('ix_activity_logs_resource_type', 'activity_logs', ['resource_type'], unique=False)
    op.create_index('ix_activity_logs_resource_id', 'activity_logs', ['resource_id'], unique=False)
    op.create_index('ix_comments_resource_type', 'comments', ['resource_type'], unique=False)
    op.create_index('ix_comments_resource_id', 'comments', ['resource_id'], unique=False)
    op.create_index('ix_comments_author_id', 'comments', ['author_id'], unique=False)
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
    op.create_index('ix_notifications_notification_type', 'notifications', ['notification_type'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop indexes
    op.drop_index('ix_notifications_notification_type', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index('ix_comments_author_id', table_name='comments')
    op.drop_index('ix_comments_resource_id', table_name='comments')
    op.drop_index('ix_comments_resource_type', table_name='comments')
    op.drop_index('ix_activity_logs_resource_id', table_name='activity_logs')
    op.drop_index('ix_activity_logs_resource_type', table_name='activity_logs')
    op.drop_index('ix_activity_logs_action', table_name='activity_logs')
    op.drop_index('ix_activity_logs_user_id', table_name='activity_logs')
    op.drop_index('ix_collaboration_sessions_created_by', table_name='collaboration_sessions')
    op.drop_index('ix_shared_resources_shared_with_user_id', table_name='shared_resources')
    op.drop_index('ix_shared_resources_owner_id', table_name='shared_resources')
    op.drop_index('ix_shared_resources_resource_id', table_name='shared_resources')
    op.drop_index('ix_shared_resources_resource_type', 'shared_resources')

    # Drop tables
    op.drop_table('notifications')
    op.drop_table('comments')
    op.drop_table('activity_logs')
    op.drop_table('session_participants')
    op.drop_table('collaboration_sessions')
    op.drop_table('shared_resources')
