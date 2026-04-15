"""add strategies and strategy_messages tables, strategy_id FK on backtests

Revision ID: a1b2c3d4e5f6
Revises: 79d8a9a381f3
Create Date: 2026-04-15 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "79d8a9a381f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- strategies table --
    op.create_table(
        "strategies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="idle"),
        sa.Column("final_rule", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("llm_history_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategies_id", "strategies", ["id"])
    op.create_index("ix_strategies_status", "strategies", ["status"])
    op.create_index("ix_strategies_created_at", "strategies", ["created_at"])

    # -- strategy_messages table --
    op.create_table(
        "strategy_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("strategy_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["strategy_id"], ["strategies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_messages_id", "strategy_messages", ["id"])
    op.create_index(
        "ix_strategy_messages_strategy_id", "strategy_messages", ["strategy_id"]
    )

    # -- Add strategy_id FK to backtests --
    op.add_column(
        "backtests",
        sa.Column("strategy_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_backtests_strategy_id",
        "backtests",
        "strategies",
        ["strategy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_backtests_strategy_id", "backtests", ["strategy_id"])

    # -- Add scores_json to backtests --
    op.add_column(
        "backtests",
        sa.Column("scores_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtests", "scores_json")
    op.drop_index("ix_backtests_strategy_id", table_name="backtests")
    op.drop_constraint("fk_backtests_strategy_id", "backtests", type_="foreignkey")
    op.drop_column("backtests", "strategy_id")
    op.drop_table("strategy_messages")
    op.drop_table("strategies")
