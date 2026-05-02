"""drop rs_pct_* + market_regime; add stop_loss_price to backtest_investments

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-02 00:00:00.000000

Drops:
- ``market_regime`` table (regime fields removed from indicator usage).
- ``rs_pct_{4,13,26,52}w`` columns from ``stock_indicators`` (relative strength
  vs benchmark removed).

Adds:
- ``stop_loss_price`` column on ``backtest_investments`` to record the per-position
  stop level used (``None`` when no stop loss was configured).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RS_COLUMNS = ["rs_pct_4w", "rs_pct_13w", "rs_pct_26w", "rs_pct_52w"]


def upgrade() -> None:
    # Drop market_regime table
    op.drop_index("ix_market_regime_date", table_name="market_regime")
    op.drop_index("ix_market_regime_index", table_name="market_regime")
    op.drop_table("market_regime")

    # Drop rs_pct_* columns from stock_indicators
    for col_name in _RS_COLUMNS:
        op.drop_column("stock_indicators", col_name)

    # Add stop_loss_price column on backtest_investments (nullable)
    op.add_column(
        "backtest_investments",
        sa.Column("stop_loss_price", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtest_investments", "stop_loss_price")

    for col_name in _RS_COLUMNS:
        op.add_column(
            "stock_indicators",
            sa.Column(col_name, sa.Float(), nullable=False, server_default="0"),
        )

    op.create_table(
        "market_regime",
        sa.Column("index", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("index_above_ma50", sa.Integer(), nullable=False),
        sa.Column("index_above_ma200", sa.Integer(), nullable=False),
        sa.Column("index_drawdown_pct_52w", sa.Float(), nullable=False),
        sa.Column("breadth_pct_above_ma50", sa.Float(), nullable=False),
        sa.Column("breadth_pct_above_ma200", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("index", "date"),
    )
    op.create_index("ix_market_regime_index", "market_regime", ["index"])
    op.create_index("ix_market_regime_date", "market_regime", ["date"])
