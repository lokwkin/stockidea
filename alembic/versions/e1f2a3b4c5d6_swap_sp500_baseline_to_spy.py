"""swap SP500 baseline data source from ^GSPC to SPY (dividend-adjusted)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-05-02 00:10:00.000000

The SP500 baseline previously used ^GSPC (raw index, unadjusted) while
individual stocks used dividend-adjusted prices. That mismatch gave the
strategy ~1.5-2%/yr "free" yield over the baseline. We now proxy SP500 with
SPY via FMP's dividend-adjusted endpoint so baseline returns include
reinvested dividends — apples-to-apples vs. the strategy.

Old DBStockPrice rows for symbol='SP500' were ^GSPC values (~$5000 scale).
SPY values are on a ~$500 scale. Mixing them in the same table would corrupt
backtest baselines, so this migration deletes the old rows and invalidates
the metadata so the next ``ensure_index_prices_fresh`` call refetches from SPY.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM stock_prices WHERE symbol = 'SP500'")
    op.execute("DELETE FROM stock_price_metadata WHERE symbol = 'SP500'")


def downgrade() -> None:
    # Nothing to undo — SP500 prices will be refetched (now from SPY) on next
    # call to ensure_index_prices_fresh.
    pass
