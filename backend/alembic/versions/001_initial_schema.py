"""Initial schema — telegram_accounts and analysis_jobs

Revision ID: 001
Revises:
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("api_id", sa.Integer(), nullable=False),
        sa.Column("api_hash", sa.String(), nullable=False),
        sa.Column("session_string", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default="active"
        ),
        sa.Column(
            "last_used_at", sa.DateTime(), nullable=True
        ),
        sa.Column(
            "rate_limited_until", sa.DateTime(), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index(
        "ix_telegram_accounts_phone_number",
        "telegram_accounts",
        ["phone_number"],
    )

    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default="pending"
        ),
        sa.Column("photo_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("photo_filename", sa.String(), nullable=False),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "telegram_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["telegram_account_id"], ["telegram_accounts.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_jobs_status", "analysis_jobs", ["status"]
    )
    op.create_index(
        "ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_created_at", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index(
        "ix_telegram_accounts_phone_number", table_name="telegram_accounts"
    )
    op.drop_table("telegram_accounts")
