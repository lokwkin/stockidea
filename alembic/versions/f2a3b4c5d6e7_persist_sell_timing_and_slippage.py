"""persist sell_timing and slippage_pct on backtests

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-02 00:30:00.000000

Both knobs were previously runtime-only — when a backtest was reloaded from
the DB, BacktestConfig fell back to the model defaults (sell_timing
'friday_close', slippage_pct 0.5) regardless of what the original run used.
Persist them so the recorded config faithfully reflects how the backtest ran.

Existing rows get NULL on both columns; the loader maps NULL → model default
so legacy backtests still display a sensible value.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "backtests",
        sa.Column("sell_timing", sa.String(), nullable=True),
    )
    op.add_column(
        "backtests",
        sa.Column("slippage_pct", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtests", "slippage_pct")
    op.drop_column("backtests", "sell_timing")
