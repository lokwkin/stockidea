"""add slope_pct_4w + acceleration_pct_{4w,26w,52w} indicator columns

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-05-04 00:00:00.000000

Expands the momentum-shape indicator family from a single 13-week acceleration
into 4w/13w/26w/52w windows, and adds back ``slope_pct_4w`` (previously
discarded as too noisy) for symmetry with the other slope windows.

The new columns are added with ``server_default='0'`` so existing rows can be
backfilled, then the table is truncated so the next compute pass produces real
values rather than zeros (existing 0.0 backfills would silently feed wrong
signals into rule/sort expressions otherwise). The truncate matches the
invalidation pattern from b8c9d0e1f2a3.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stock_indicators",
        sa.Column("slope_pct_4w", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "stock_indicators",
        sa.Column(
            "acceleration_pct_4w", sa.Float(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "stock_indicators",
        sa.Column(
            "acceleration_pct_26w", sa.Float(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "stock_indicators",
        sa.Column(
            "acceleration_pct_52w", sa.Float(), nullable=False, server_default="0"
        ),
    )
    # Drop cached rows so next access recomputes with real values for the new fields.
    op.execute("DELETE FROM stock_indicators")


def downgrade() -> None:
    op.drop_column("stock_indicators", "acceleration_pct_52w")
    op.drop_column("stock_indicators", "acceleration_pct_26w")
    op.drop_column("stock_indicators", "acceleration_pct_4w")
    op.drop_column("stock_indicators", "slope_pct_4w")
