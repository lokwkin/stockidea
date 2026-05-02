"""convert stop_loss_json from type/value/ma_period to expression form

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-02 21:00:00.000000

StopLossConfig is now a single ``expression`` field evaluated at buy time
against ``buy_price`` + ``sma_{20,50,100,200}``. Convert legacy rows in place:

    {"type":"percent","value":N}              → {"expression":"buy_price * <1-N/100>"}
    {"type":"ma_percent","value":N,"ma_period":P} → {"expression":"sma_<P> * <N/100>"}

Schema is unchanged (still a Text column ``stop_loss_json``); only the JSON
payload is rewritten.
"""

from __future__ import annotations

import json
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _legacy_to_expression(payload: dict) -> dict:
    if "expression" in payload:
        return payload  # already migrated
    t = payload.get("type")
    value = payload.get("value")
    if t == "percent":
        return {"expression": f"buy_price * {1 - float(value) / 100:g}"}
    if t == "ma_percent":
        ma_period = payload.get("ma_period")
        return {"expression": f"sma_{int(ma_period)} * {float(value) / 100:g}"}
    raise ValueError(f"Unknown legacy stop_loss payload: {payload!r}")


def _expression_to_legacy(payload: dict) -> dict:
    """Best-effort reverse — only the two shapes upgrade() emits."""
    if "type" in payload:
        return payload
    expr = payload.get("expression", "").strip()
    m = re.fullmatch(r"buy_price\s*\*\s*([\d.]+)", expr)
    if m:
        factor = float(m.group(1))
        return {"type": "percent", "value": (1.0 - factor) * 100.0}
    m = re.fullmatch(r"sma_(\d+)\s*\*\s*([\d.]+)", expr)
    if m:
        return {
            "type": "ma_percent",
            "ma_period": int(m.group(1)),
            "value": float(m.group(2)) * 100.0,
        }
    return payload


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, stop_loss_json FROM backtests WHERE stop_loss_json IS NOT NULL"
        )
    ).fetchall()
    for row_id, raw in rows:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        new_payload = _legacy_to_expression(payload)
        bind.execute(
            sa.text("UPDATE backtests SET stop_loss_json = :payload WHERE id = :id"),
            {"payload": json.dumps(new_payload), "id": row_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, stop_loss_json FROM backtests WHERE stop_loss_json IS NOT NULL"
        )
    ).fetchall()
    for row_id, raw in rows:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        new_payload = _expression_to_legacy(payload)
        bind.execute(
            sa.text("UPDATE backtests SET stop_loss_json = :payload WHERE id = :id"),
            {"payload": json.dumps(new_payload), "id": row_id},
        )
