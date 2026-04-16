"""API routes for indicator operations."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn
from stockidea.indicators import service as indicators_service
from stockidea.rule_engine import DEFAULT_RANKING, compile_ranking, compile_rule
from stockidea.types import StockIndex

router = APIRouter()


@router.get("/indicators")
async def list_analysis() -> list[str]:
    async with conn.get_db_session() as db_session:
        dates = await indicators_service.list_indicator_dates(db_session)
    return [date.strftime("%Y-%m-%d") for date in dates]


@router.get("/indicators/{date}/")
async def get_analysis(
    date: str,
    rule: Optional[str] = None,
    ranking: Optional[str] = None,
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

    if rule:
        try:
            rule_func = compile_rule(rule)
            ranking_func = compile_ranking(ranking or DEFAULT_RANKING)
            stock_indicators_batch = indicators_service.apply_rule(
                stock_indicators_batch,
                rule_func=rule_func,
                ranking_func=ranking_func,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    return {
        "date": indicators_date.strftime("%Y-%m-%d"),
        "data": [
            stock_indicator.model_dump() for stock_indicator in stock_indicators_batch
        ],
    }
