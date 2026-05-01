"""add regime, MA structure, and relative strength indicators

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-17 00:00:00.000000

Adds:
- 9 new columns on ``stock_indicators`` (price_vs_ma{20,50,100,200}_pct,
  ma50_vs_ma200_pct, rs_pct_{4,13,26,52}w) — defaulted to 0 so existing
  rows still validate; recompute via CLI ``compute -d <date>`` to backfill.
- New ``stock_sma`` + ``stock_sma_metadata`` tables — caches FMP SMA series
  (per symbol, per period_length) with the standard 1-day TTL pattern.
- New ``market_regime`` table — one row per ``(index, date)``; merged onto
  ``StockIndicators`` at read time as flat ``mkt_*`` fields.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_INDICATOR_COLUMNS = [
    "price_vs_ma20_pct",
    "price_vs_ma50_pct",
    "price_vs_ma100_pct",
    "price_vs_ma200_pct",
    "ma50_vs_ma200_pct",
    "rs_pct_4w",
    "rs_pct_13w",
    "rs_pct_26w",
    "rs_pct_52w",
]


def upgrade() -> None:
    # New columns on stock_indicators (default 0 so existing rows validate)
    for col_name in _NEW_INDICATOR_COLUMNS:
        op.add_column(
            "stock_indicators",
            sa.Column(col_name, sa.Float(), nullable=False, server_default="0"),
        )

    # Cached FMP SMA series
    op.create_table(
        "stock_sma",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("period_length", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sma_value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "period_length", "date"),
    )
    op.create_index("ix_stock_sma_symbol", "stock_sma", ["symbol"])
    op.create_index("ix_stock_sma_period_length", "stock_sma", ["period_length"])
    op.create_index("ix_stock_sma_date", "stock_sma", ["date"])

    op.create_table(
        "stock_sma_metadata",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("period_length", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "period_length"),
    )
    op.create_index(
        "ix_stock_sma_metadata_symbol", "stock_sma_metadata", ["symbol"]
    )
    op.create_index(
        "ix_stock_sma_metadata_period_length",
        "stock_sma_metadata",
        ["period_length"],
    )

    # Per-(index, date) market regime — merged at read time
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


def downgrade() -> None:
    op.drop_index("ix_market_regime_date", table_name="market_regime")
    op.drop_index("ix_market_regime_index", table_name="market_regime")
    op.drop_table("market_regime")

    op.drop_index(
        "ix_stock_sma_metadata_period_length", table_name="stock_sma_metadata"
    )
    op.drop_index("ix_stock_sma_metadata_symbol", table_name="stock_sma_metadata")
    op.drop_table("stock_sma_metadata")

    op.drop_index("ix_stock_sma_date", table_name="stock_sma")
    op.drop_index("ix_stock_sma_period_length", table_name="stock_sma")
    op.drop_index("ix_stock_sma_symbol", table_name="stock_sma")
    op.drop_table("stock_sma")

    for col_name in reversed(_NEW_INDICATOR_COLUMNS):
        op.drop_column("stock_indicators", col_name)
