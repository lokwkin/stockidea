"""standardize indicator naming + add windowed variants

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-17 00:00:00.000000

Drops and recreates the ``stock_indicators`` table with the new
``<metric>_<unit>_<window>`` column naming and additional windowed
variants (log slope/R² at 13w/26w/52w, drawdown at 4w/13w/26w,
% up-weeks at 4w/13w/26w). All existing rows are discarded —
indicators must be recomputed (CLI: ``compute -d <date>``).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("stock_indicators")
    op.create_table(
        "stock_indicators",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_weeks", sa.Integer(), nullable=False),
        # Slope (linear regression)
        sa.Column("slope_pct_13w", sa.Float(), nullable=False),
        sa.Column("slope_pct_26w", sa.Float(), nullable=False),
        sa.Column("slope_pct_52w", sa.Float(), nullable=False),
        # R² (linear regression)
        sa.Column("r_squared_4w", sa.Float(), nullable=False),
        sa.Column("r_squared_13w", sa.Float(), nullable=False),
        sa.Column("r_squared_26w", sa.Float(), nullable=False),
        sa.Column("r_squared_52w", sa.Float(), nullable=False),
        # Log regression
        sa.Column("log_slope_13w", sa.Float(), nullable=False),
        sa.Column("log_r_squared_13w", sa.Float(), nullable=False),
        sa.Column("log_slope_26w", sa.Float(), nullable=False),
        sa.Column("log_r_squared_26w", sa.Float(), nullable=False),
        sa.Column("log_slope_52w", sa.Float(), nullable=False),
        sa.Column("log_r_squared_52w", sa.Float(), nullable=False),
        # Point-to-point change
        sa.Column("change_pct_1w", sa.Float(), nullable=False),
        sa.Column("change_pct_2w", sa.Float(), nullable=False),
        sa.Column("change_pct_4w", sa.Float(), nullable=False),
        sa.Column("change_pct_13w", sa.Float(), nullable=False),
        sa.Column("change_pct_26w", sa.Float(), nullable=False),
        sa.Column("change_pct_52w", sa.Float(), nullable=False),
        # Max single-period swing
        sa.Column("max_jump_pct_1w", sa.Float(), nullable=False),
        sa.Column("max_drop_pct_1w", sa.Float(), nullable=False),
        sa.Column("max_jump_pct_2w", sa.Float(), nullable=False),
        sa.Column("max_drop_pct_2w", sa.Float(), nullable=False),
        sa.Column("max_jump_pct_4w", sa.Float(), nullable=False),
        sa.Column("max_drop_pct_4w", sa.Float(), nullable=False),
        # Weekly return std-dev
        sa.Column("return_std_52w", sa.Float(), nullable=False),
        sa.Column("downside_std_52w", sa.Float(), nullable=False),
        # Max drawdown
        sa.Column("max_drawdown_pct_4w", sa.Float(), nullable=False),
        sa.Column("max_drawdown_pct_13w", sa.Float(), nullable=False),
        sa.Column("max_drawdown_pct_26w", sa.Float(), nullable=False),
        sa.Column("max_drawdown_pct_52w", sa.Float(), nullable=False),
        # % up-weeks
        sa.Column("pct_weeks_positive_4w", sa.Float(), nullable=False),
        sa.Column("pct_weeks_positive_13w", sa.Float(), nullable=False),
        sa.Column("pct_weeks_positive_26w", sa.Float(), nullable=False),
        sa.Column("pct_weeks_positive_52w", sa.Float(), nullable=False),
        # Momentum shape
        sa.Column("acceleration_pct_13w", sa.Float(), nullable=False),
        sa.Column("from_high_pct_4w", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )
    op.create_index("ix_stock_indicators_symbol", "stock_indicators", ["symbol"])
    op.create_index("ix_stock_indicators_date", "stock_indicators", ["date"])


def downgrade() -> None:
    op.drop_table("stock_indicators")
    op.create_table(
        "stock_indicators",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_weeks", sa.Integer(), nullable=False),
        sa.Column("linear_slope_pct", sa.Float(), nullable=False),
        sa.Column("linear_r_squared", sa.Float(), nullable=False),
        sa.Column("log_slope", sa.Float(), nullable=False),
        sa.Column("log_r_squared", sa.Float(), nullable=False),
        sa.Column("change_1w_pct", sa.Float(), nullable=False),
        sa.Column("change_2w_pct", sa.Float(), nullable=False),
        sa.Column("change_4w_pct", sa.Float(), nullable=False),
        sa.Column("change_13w_pct", sa.Float(), nullable=False),
        sa.Column("change_26w_pct", sa.Float(), nullable=False),
        sa.Column("change_1y_pct", sa.Float(), nullable=False),
        sa.Column("max_jump_1w_pct", sa.Float(), nullable=False),
        sa.Column("max_drop_1w_pct", sa.Float(), nullable=False),
        sa.Column("max_jump_2w_pct", sa.Float(), nullable=False),
        sa.Column("max_drop_2w_pct", sa.Float(), nullable=False),
        sa.Column("max_jump_4w_pct", sa.Float(), nullable=False),
        sa.Column("max_drop_4w_pct", sa.Float(), nullable=False),
        sa.Column("weekly_return_std", sa.Float(), nullable=False),
        sa.Column("downside_std", sa.Float(), nullable=False),
        sa.Column("max_drawdown_pct", sa.Float(), nullable=False),
        sa.Column("pct_weeks_positive", sa.Float(), nullable=False),
        sa.Column("slope_13w_pct", sa.Float(), nullable=False),
        sa.Column("r_squared_13w", sa.Float(), nullable=False),
        sa.Column("r_squared_4w", sa.Float(), nullable=False),
        sa.Column("slope_26w_pct", sa.Float(), nullable=False),
        sa.Column("r_squared_26w", sa.Float(), nullable=False),
        sa.Column("acceleration_13w", sa.Float(), nullable=False),
        sa.Column("pct_from_4w_high", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )
    op.create_index("ix_stock_indicators_symbol", "stock_indicators", ["symbol"])
    op.create_index("ix_stock_indicators_date", "stock_indicators", ["date"])
