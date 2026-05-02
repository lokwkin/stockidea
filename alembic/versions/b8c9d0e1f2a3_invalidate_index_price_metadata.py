"""invalidate index price metadata so OHLC refetch happens

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-02 00:00:00.000000

Index prices were previously fetched from FMP's ``/historical-price-eod/light``
endpoint which only returns ``{price, volume}`` — leaving ``open`` NULL on
``stock_prices`` rows for index symbols. The backtester now buys at Monday open
and sells at Friday close for both stocks and the baseline, so index rows need
``open`` populated.

This migration deletes the metadata rows for SP500 / NASDAQ so the next call to
``ensure_index_prices_fresh`` triggers a full refetch via the new
``/historical-price-eod/full`` endpoint, which includes OHLC.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM stock_price_metadata WHERE symbol IN ('SP500', 'NASDAQ')"
    )


def downgrade() -> None:
    # Nothing to undo — metadata will be recreated on next fetch.
    pass
