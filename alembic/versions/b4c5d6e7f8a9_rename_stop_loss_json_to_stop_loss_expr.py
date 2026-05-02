"""rename backtests.stop_loss_json -> stop_loss_expr (plain text expression)

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-05-02 21:30:00.000000

After collapsing StopLossConfig to a single ``expression`` field, the
JSON-wrapped column carries no extra information. Rename the column to
``stop_loss_expr`` and store the expression as a plain string. Backfill
by extracting ``$.expression`` from each existing row's JSON payload.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "backtests",
        sa.Column("stop_loss_expr", sa.Text(), nullable=True),
    )
    # Cast the Text JSON to jsonb and pull out the `expression` field.
    op.execute(
        "UPDATE backtests "
        "SET stop_loss_expr = (stop_loss_json::jsonb)->>'expression' "
        "WHERE stop_loss_json IS NOT NULL"
    )
    op.drop_column("backtests", "stop_loss_json")


def downgrade() -> None:
    op.add_column(
        "backtests",
        sa.Column("stop_loss_json", sa.Text(), nullable=True),
    )
    # Wrap the plain expression back into the JSON shape used by upgrade().
    op.execute(
        "UPDATE backtests "
        "SET stop_loss_json = json_build_object('expression', stop_loss_expr)::text "
        "WHERE stop_loss_expr IS NOT NULL"
    )
    op.drop_column("backtests", "stop_loss_expr")
