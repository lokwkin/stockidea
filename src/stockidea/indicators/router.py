"""API routes for indicator operations."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn
from stockidea.indicators import service as indicators_service
from stockidea.rule_engine import DEFAULT_SORT, compile_rule, compile_sort
from stockidea.types import StockIndex

router = APIRouter()


@router.get("/indicators")
async def list_analysis() -> list[str]:
    async with conn.get_db_session() as db_session:
        dates = await indicators_service.list_indicator_dates(db_session)
    return [date.strftime("%Y-%m-%d") for date in dates]


@router.get("/indicators/symbol/{symbol}/latest")
async def get_latest_indicators_for_symbol(symbol: str) -> dict:
    """Return the most recent indicators for a single stock symbol."""
    async with conn.get_db_session() as db_session:
        dates = await indicators_service.list_indicator_dates(db_session)
        if not dates:
            return {"data": None}

        from stockidea.datasource.database import queries

        for dt in dates:
            indicators = await queries.load_stock_indicators(
                db_session, symbol.upper(), dt.date()
            )
            if indicators:
                return {
                    "date": dt.strftime("%Y-%m-%d"),
                    "data": indicators.model_dump(),
                }

        return {"data": None}


@router.get("/indicators/symbol/{symbol}/{date}")
async def get_indicators_for_symbol_at_date(symbol: str, date: str) -> dict:
    """Return indicators for a single stock at a specific date.

    Computes on-the-fly if not already stored in the database.
    """
    indicators_date = datetime.strptime(date, "%Y-%m-%d")

    async with conn.get_db_session() as db_session:
        results = await indicators_service.get_stock_indicators_batch(
            db_session,
            symbols=[symbol.upper()],
            indicators_date=indicators_date,
            back_period_weeks=52,
            compute_if_not_exists=True,
        )

    if not results:
        return {"data": None}

    return {
        "date": indicators_date.strftime("%Y-%m-%d"),
        "data": results[0].model_dump(),
    }


@router.get("/indicators/{date}/")
async def get_analysis(
    date: str,
    rule: Optional[str] = None,
    sort_expr: Optional[str] = None,
    max_stocks: Optional[int] = None,
    index: StockIndex = StockIndex.SP500,
) -> dict:

    indicators_date = datetime.strptime(date, "%Y-%m-%d")

    async with conn.get_db_session() as db_session:
        symbols = await datasource_service.get_constituent_at(
            db_session, index, indicators_date.date()
        )
        stock_indicators_batch = await indicators_service.get_stock_indicators_batch(
            db_session,
            symbols=symbols,
            indicators_date=indicators_date,
            back_period_weeks=52,
        )

    # Apply rule/sort whenever any of rule, sort_expr, or max_stocks is provided.
    if rule or sort_expr or max_stocks is not None:
        try:
            rule_func = compile_rule(rule) if rule else None
            sort_func = compile_sort(sort_expr or DEFAULT_SORT)
            stock_indicators_batch = indicators_service.apply_rule(
                stock_indicators_batch,
                rule_func=rule_func,
                sort_func=sort_func,
            )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid rule/sort expression: {e}"
            )

        if max_stocks is not None and max_stocks > 0:
            stock_indicators_batch = stock_indicators_batch[:max_stocks]

    return {
        "date": indicators_date.strftime("%Y-%m-%d"),
        "data": [
            stock_indicator.model_dump() for stock_indicator in stock_indicators_batch
        ],
    }
