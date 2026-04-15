"""initial schema

Revision ID: 79d8a9a381f3
Revises:
Create Date: 2026-04-15 16:27:25.756134

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "79d8a9a381f3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables from scratch."""
    # -- Standalone tables (no foreign keys) --

    op.create_table(
        "constituent_changes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("index", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("added_symbol", sa.String(), nullable=True),
        sa.Column("removed_symbol", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_constituent_changes_index", "constituent_changes", ["index"])

    op.create_table(
        "constituent_metadata",
        sa.Column("index", sa.String(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("index"),
    )

    op.create_table(
        "stock_prices",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("adj_close", sa.Float(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )
    op.create_index("ix_stock_prices_symbol", "stock_prices", ["symbol"])
    op.create_index("ix_stock_prices_date", "stock_prices", ["date"])

    op.create_table(
        "stock_price_metadata",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )
    op.create_index(
        "ix_stock_price_metadata_symbol", "stock_price_metadata", ["symbol"]
    )

    op.create_table(
        "stock_metrics",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_weeks", sa.Integer(), nullable=False),
        # Trend metrics
        sa.Column("linear_slope_pct", sa.Float(), nullable=False),
        sa.Column("linear_r_squared", sa.Float(), nullable=False),
        sa.Column("log_slope", sa.Float(), nullable=False),
        sa.Column("log_r_squared", sa.Float(), nullable=False),
        # Return metrics
        sa.Column("change_1w_pct", sa.Float(), nullable=False),
        sa.Column("change_2w_pct", sa.Float(), nullable=False),
        sa.Column("change_4w_pct", sa.Float(), nullable=False),
        sa.Column("change_13w_pct", sa.Float(), nullable=False),
        sa.Column("change_26w_pct", sa.Float(), nullable=False),
        sa.Column("change_1y_pct", sa.Float(), nullable=False),
        # Volatility metrics
        sa.Column("max_jump_1w_pct", sa.Float(), nullable=False),
        sa.Column("max_drop_1w_pct", sa.Float(), nullable=False),
        sa.Column("max_jump_2w_pct", sa.Float(), nullable=False),
        sa.Column("max_drop_2w_pct", sa.Float(), nullable=False),
        sa.Column("max_jump_4w_pct", sa.Float(), nullable=False),
        sa.Column("max_drop_4w_pct", sa.Float(), nullable=False),
        # Stability metrics
        sa.Column("max_drawdown_pct", sa.Float(), nullable=False),
        sa.Column("pct_weeks_positive", sa.Float(), nullable=False),
        sa.Column("slope_13w_pct", sa.Float(), nullable=False),
        sa.Column("r_squared_13w", sa.Float(), nullable=False),
        sa.Column("slope_26w_pct", sa.Float(), nullable=False),
        sa.Column("r_squared_26w", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )
    op.create_index("ix_stock_metrics_symbol", "stock_metrics", ["symbol"])
    op.create_index("ix_stock_metrics_date", "stock_metrics", ["date"])

    op.create_table(
        "simulations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("initial_balance", sa.Float(), nullable=False),
        sa.Column("final_balance", sa.Float(), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=False),
        sa.Column("profit_pct", sa.Float(), nullable=False),
        sa.Column("profit", sa.Float(), nullable=False),
        sa.Column("baseline_index", sa.String(), nullable=False),
        sa.Column("baseline_profit_pct", sa.Float(), nullable=False),
        sa.Column("baseline_profit", sa.Float(), nullable=False),
        sa.Column("baseline_balance", sa.Float(), nullable=False),
        sa.Column("max_stocks", sa.Integer(), nullable=False),
        sa.Column("rebalance_interval_weeks", sa.Integer(), nullable=False),
        sa.Column("rule", sa.Text(), nullable=False),
        sa.Column("index", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulations_id", "simulations", ["id"])
    op.create_index("ix_simulations_date_start", "simulations", ["date_start"])
    op.create_index("ix_simulations_date_end", "simulations", ["date_end"])
    op.create_index("ix_simulations_created_at", "simulations", ["created_at"])

    # -- Tables with foreign keys --

    op.create_table(
        "rebalance_histories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("simulation_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("profit_pct", sa.Float(), nullable=False),
        sa.Column("profit", sa.Float(), nullable=False),
        sa.Column("baseline_profit_pct", sa.Float(), nullable=False),
        sa.Column("baseline_profit", sa.Float(), nullable=False),
        sa.Column("baseline_balance", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["simulation_id"], ["simulations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rebalance_histories_id", "rebalance_histories", ["id"])
    op.create_index(
        "ix_rebalance_histories_simulation_id",
        "rebalance_histories",
        ["simulation_id"],
    )
    op.create_index("ix_rebalance_histories_date", "rebalance_histories", ["date"])

    op.create_table(
        "simulation_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("simulation_id", sa.UUID(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["simulation_id"], ["simulations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_jobs_id", "simulation_jobs", ["id"])
    op.create_index("ix_simulation_jobs_status", "simulation_jobs", ["status"])
    op.create_index(
        "ix_simulation_jobs_created_at", "simulation_jobs", ["created_at"]
    )

    op.create_table(
        "investments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("rebalance_history_id", sa.UUID(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("position", sa.Float(), nullable=False),
        sa.Column("buy_price", sa.Float(), nullable=False),
        sa.Column("buy_date", sa.Date(), nullable=False),
        sa.Column("sell_price", sa.Float(), nullable=False),
        sa.Column("sell_date", sa.Date(), nullable=False),
        sa.Column("profit_pct", sa.Float(), nullable=False),
        sa.Column("profit", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rebalance_history_id"],
            ["rebalance_histories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_investments_id", "investments", ["id"])
    op.create_index(
        "ix_investments_rebalance_history_id",
        "investments",
        ["rebalance_history_id"],
    )
    op.create_index("ix_investments_symbol", "investments", ["symbol"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("investments")
    op.drop_table("simulation_jobs")
    op.drop_table("rebalance_histories")
    op.drop_table("simulations")
    op.drop_table("stock_metrics")
    op.drop_table("stock_price_metadata")
    op.drop_table("stock_prices")
    op.drop_table("constituent_metadata")
    op.drop_table("constituent_changes")
