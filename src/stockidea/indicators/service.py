from datetime import datetime, timedelta
import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession


from stockidea.indicators import calculator
from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import queries
from stockidea.types import StockIndicators

logger = logging.getLogger(__name__)


def apply_rule(
    indicators_batch: list[StockIndicators],
    rule_func: Callable[[StockIndicators], bool] | None = None,
    ranking_func: Callable[[StockIndicators], float] | None = None,
) -> list[StockIndicators]:
    from stockidea.rule_engine import compile_ranking, DEFAULT_RANKING

    if rule_func is None:
        filtered_stocks = list(indicators_batch)
    else:
        filtered_stocks = [
            indicator for indicator in indicators_batch if rule_func(indicator)
        ]

    # Rank by expression (default: risk-adjusted momentum)
    if ranking_func is None:
        ranking_func = compile_ranking(DEFAULT_RANKING)
    filtered_stocks = calculator.rank_by_expression(filtered_stocks, ranking_func)

    # Remove outliers based on the linear slope percentage
    filtered_stocks = calculator.slope_outlier_mask(filtered_stocks, k=3.0)

    return filtered_stocks


async def get_stock_indicators_batch(
    db_session: AsyncSession,
    symbols: list[str],
    indicators_date: datetime,
    back_period_weeks: int = 52,
    compute_if_not_exists: bool = False,
) -> list[StockIndicators]:
    from_date = indicators_date - timedelta(weeks=back_period_weeks)
    to_date = indicators_date

    results: list[StockIndicators] = []
    for symbol in symbols:
        try:
            # Try to load from database first
            stock_indicators = await queries.load_stock_indicators(
                db_session, symbol, indicators_date.date()
            )
            if not stock_indicators and compute_if_not_exists:
                prices = await datasource_service.get_stock_price_history(
                    db_session, symbol, from_date, to_date
                )

                stock_indicators = calculator.compute_stock_indicators(
                    symbol=symbol,
                    prices=prices,
                    from_date=indicators_date - timedelta(weeks=back_period_weeks),
                    to_date=indicators_date,
                )
                # Save to database for cache
                await queries.save_stock_indicators(
                    db_session, stock_indicators, indicators_date.date()
                )

            if stock_indicators:
                results.append(stock_indicators)
        except Exception as e:
            logger.error(f"Error computing stock indicators for {symbol}: {e}")

    return results


async def list_indicator_dates(db_session: AsyncSession) -> list[datetime]:
    return await queries.list_indicator_dates(db_session)
