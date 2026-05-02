"""drop unused backtest_jobs table

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-05-02 00:00:00.000000

The ``backtest_jobs`` table was introduced for an asynchronous job queue that
never went into use — the current ``POST /backtest`` endpoint runs the
backtester synchronously and persists the result directly into ``backtests``.
Dropping the orphan table and its indexes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_backtest_jobs_created_at", table_name="backtest_jobs")
    op.drop_index("ix_backtest_jobs_status", table_name="backtest_jobs")
    op.drop_index("ix_backtest_jobs_id", table_name="backtest_jobs")
    op.drop_table("backtest_jobs")


def downgrade() -> None:
    op.create_table(
        "backtest_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("backtest_id", sa.UUID(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_jobs_id", "backtest_jobs", ["id"])
    op.create_index("ix_backtest_jobs_status", "backtest_jobs", ["status"])
    op.create_index("ix_backtest_jobs_created_at", "backtest_jobs", ["created_at"])
