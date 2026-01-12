"""Initial migration

Revision ID: 001
Revises:
Create Date: 2025-01-03 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('last_login', sa.String(length=255), nullable=True),
        sa.Column('login_attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Create data_sources table
    op.create_table(
        'data_sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('api_version', sa.String(length=20), nullable=True),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.Column('total_ingestions', sa.Integer(), nullable=False),
        sa.Column('successful_ingestions', sa.Integer(), nullable=False),
        sa.Column('failed_ingestions', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_successful_ingestion', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create raw_documents table
    op.create_table(
        'raw_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.Column('processing_attempts', sa.Integer(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content_quality_score', sa.Float(), nullable=True),
        sa.Column('duplicate_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ingestion_logs table
    op.create_table(
        'ingestion_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operation_id', sa.String(length=255), nullable=False),
        sa.Column('ingestion_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data_source_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('records_processed', sa.Integer(), nullable=False),
        sa.Column('records_successful', sa.Integer(), nullable=False),
        sa.Column('records_failed', sa.Integer(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('throughput_per_second', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operation_id')
    )

    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
    op.create_index('ix_data_sources_type', 'data_sources', ['type'], unique=False)
    op.create_index('ix_data_sources_name', 'data_sources', ['name'], unique=False)
    op.create_index('ix_raw_documents_source_type', 'raw_documents', ['source_type'], unique=False)
    op.create_index('ix_raw_documents_title', 'raw_documents', ['title'], unique=False)
    op.create_index('ix_raw_documents_source_id', 'raw_documents', ['source_id'], unique=False)
    op.create_index('ix_raw_documents_external_id', 'raw_documents', ['external_id'], unique=False)
    op.create_index('ix_ingestion_logs_operation_id', 'ingestion_logs', ['operation_id'], unique=False)
    op.create_index('ix_ingestion_logs_ingestion_type', 'ingestion_logs', ['ingestion_type'], unique=False)
    op.create_index('ix_ingestion_logs_status', 'ingestion_logs', ['status'], unique=False)
    op.create_index('ix_ingestion_logs_data_source_id', 'ingestion_logs', ['data_source_id'], unique=False)
    op.create_index('ix_ingestion_logs_user_id', 'ingestion_logs', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop indexes
    op.drop_index('ix_ingestion_logs_user_id', table_name='ingestion_logs')
    op.drop_index('ix_ingestion_logs_data_source_id', table_name='ingestion_logs')
    op.drop_index('ix_ingestion_logs_status', table_name='ingestion_logs')
    op.drop_index('ix_ingestion_logs_ingestion_type', table_name='ingestion_logs')
    op.drop_index('ix_ingestion_logs_operation_id', table_name='ingestion_logs')
    op.drop_index('ix_raw_documents_external_id', table_name='raw_documents')
    op.drop_index('ix_raw_documents_source_id', table_name='raw_documents')
    op.drop_index('ix_raw_documents_title', table_name='raw_documents')
    op.drop_index('ix_raw_documents_source_type', table_name='raw_documents')
    op.drop_index('ix_data_sources_name', table_name='data_sources')
    op.drop_index('ix_data_sources_type', table_name='data_sources')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    # Drop tables
    op.drop_table('ingestion_logs')
    op.drop_table('raw_documents')
    op.drop_table('data_sources')
    op.drop_table('users')
