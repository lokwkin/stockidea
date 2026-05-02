"""rename backtests.ranking to backtests.sort_expr

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-05-02 00:00:00.000000

The ``--ranking`` CLI flag was renamed to ``--sort`` / ``-s`` so the user-facing
vocabulary is shorter and matches what the operation actually does (sorting
filtered rows). The DB column is renamed to ``sort_expr`` to stay in sync with
the renamed ``BacktestConfig.sort_expr`` field.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("backtests", "ranking", new_column_name="sort_expr")


def downgrade() -> None:
    op.alter_column("backtests", "sort_expr", new_column_name="ranking")
