
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession


from stockidea.analysis import metrics_calculator
from stockidea.datasource import market_data
from stockidea.datasource.database import conn
from stockidea.datasource.database import queries
from stockidea.types import StockMetrics

logger = logging.getLogger(__name__)


def apply_rule(stock_metrics_batch: list[StockMetrics], rule_func: Callable[[StockMetrics], bool]
               ) -> list[StockMetrics]:
    filtered_stocks = [stock_metrics for stock_metrics in stock_metrics_batch if rule_func(stock_metrics)]

    # Sort by rising stability score
    filtered_stocks = metrics_calculator.rank_by_rising_stability_score(filtered_stocks)

    # Remove outliers from the list of StockMetrics objects based on the linear slope percentage
    filtered_stocks = metrics_calculator.slope_outlier_mask(filtered_stocks, k=3.0)

    return filtered_stocks


async def get_stock_metrics_batch(
    db_session: AsyncSession,
    symbols: list[str],
    metrics_date: datetime,
    back_period_weeks: int = 52,
    compute_if_not_exists: bool = False,
) -> list[StockMetrics]:

    async def get_stock_metrics(semaphore: asyncio.Semaphore, symbol: str) -> StockMetrics | None:
        async with semaphore:
            try:
                # Try to load from database first
                stock_metrics = await queries.load_stock_metrics(db_session, symbol, metrics_date.date())
                if not stock_metrics and not compute_if_not_exists:
                    prices = await market_data.get_stock_price_history(db_session, symbol, from_date, to_date)

                    stock_metrics = metrics_calculator.compute_stock_metrics(
                        symbol=symbol,
                        prices=prices,
                        from_date=metrics_date - timedelta(weeks=back_period_weeks),
                        to_date=metrics_date,
                    )
                    # Save to database for cache
                    await queries.save_stock_metrics(db_session, stock_metrics, metrics_date.date())

                return stock_metrics
            except Exception as e:
                logger.error(f"Error computing stock metrics for {symbol}: {e}")
                return None

    from_date = metrics_date - timedelta(weeks=back_period_weeks)
    to_date = metrics_date

    semaphore = asyncio.Semaphore(30)

    tasks = [get_stock_metrics(semaphore, symbol) for symbol in symbols]
    results = [metric for metric in await asyncio.gather(*tasks) if metric is not None]

    return results


async def list_metrics_dates() -> list[datetime]:
    async with conn.get_db_session() as db_session:
        return await queries.list_metrics_dates(db_session)
