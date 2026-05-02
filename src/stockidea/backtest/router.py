"""API routes for backtest operations."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from stockidea.backtest.backtester import Backtester
from stockidea.datasource.database import conn, queries
from stockidea.rule_engine import compile_ranking, compile_rule, extract_involved_keys
from stockidea.types import BacktestConfig, StockIndex

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/backtests")
async def list_backtests() -> list[dict]:
    """Return list of available backtests from database."""
    async with conn.get_db_session() as db_session:
        backtests = await queries.list_backtests(db_session)
        return backtests


@router.get("/backtests/{backtest_id}")
async def get_backtest(backtest_id: UUID) -> dict:
    """Return the full JSON content of a backtest by ID."""
    async with conn.get_db_session() as db_session:
        backtest_result = await queries.get_backtest_by_id(db_session, backtest_id)
        if backtest_result is None:
            raise HTTPException(
                status_code=404, detail=f"Backtest not found: {backtest_id}"
            )
        return backtest_result.model_dump()


@router.post("/backtest")
async def create_backtest(backtest_config: BacktestConfig) -> dict:
    """Run a backtest synchronously and return the saved backtest ID."""
    if not backtest_config.involved_keys:
        backtest_config.involved_keys = extract_involved_keys(backtest_config.rule)

    try:
        rule_func = compile_rule(backtest_config.rule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    try:
        ranking_func = compile_ranking(backtest_config.ranking)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ranking expression: {e}")

    async with conn.get_db_session() as db_session:
        backtester = Backtester(
            db_session=db_session,
            max_stocks=backtest_config.max_stocks,
            rebalance_interval_weeks=backtest_config.rebalance_interval_weeks,
            date_start=backtest_config.date_start,
            date_end=backtest_config.date_end,
            rule_func=rule_func,
            rule_raw=backtest_config.rule,
            from_index=backtest_config.index,
            baseline_index=StockIndex.SP500,
            ranking_func=ranking_func,
            ranking_raw=backtest_config.ranking,
            stop_loss=backtest_config.stop_loss,
            sell_timing=backtest_config.sell_timing,
        )
        result = await backtester.backtest()
        backtest_id = await queries.save_backtest_result(db_session, result)

    return {"backtest_id": str(backtest_id)}
