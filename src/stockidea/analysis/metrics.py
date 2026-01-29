
from datetime import datetime, timedelta
import logging
from typing import Callable


from stockidea.analysis import metrics_calculator
from stockidea.datasource.database import conn
from stockidea.datasource.database import queries
from stockidea.datasource.database.queries import (
    save_stock_metrics,
    load_stock_metrics,
    has_metrics_for_date,
)
from stockidea.types import StockPrice, StockMetrics

logger = logging.getLogger(__name__)


def apply_rule(stock_metrics_batch: list[StockMetrics], rule_func: Callable[[StockMetrics], bool]
               ) -> list[StockMetrics]:

    filtered_stocks = [stock_metrics for stock_metrics in stock_metrics_batch if rule_func(stock_metrics)]

    # Sort by rising stability score
    filtered_stocks = metrics_calculator.rank_by_rising_stability_score(filtered_stocks)

    # Remove outliers from the list of StockMetrics objects based on the linear slope percentage
    filtered_stocks = metrics_calculator.slope_outlier_mask(filtered_stocks, k=3.0)

    return filtered_stocks


def _compute_stock_metrics_batch(
    stock_prices: dict[str, list[StockPrice]],
    metrics_date: datetime,
    back_period_weeks: int = 52,
) -> list[StockMetrics]:
    """Compute trend analyses for a batch of stocks (pure computation, no I/O)."""
    analyses: list[StockMetrics] = []
    for symbol, prices in stock_prices.items():
        analysis = metrics_calculator.compute_stock_metrics(
            symbol=symbol,
            prices=prices,
            from_date=metrics_date - timedelta(weeks=back_period_weeks),
            to_date=metrics_date,
        )
        if analysis:
            analyses.append(analysis)
    return analyses


async def compute_stock_metrics_batch(
    stock_prices: dict[str, list[StockPrice]],
    metrics_date: datetime,
    back_period_weeks: int = 52,
) -> list[StockMetrics]:
    """
    Compute stock metrics for a batch of stocks.
    Returns the list of StockMetrics objects.
    """
    stock_metrics_batch = _compute_stock_metrics_batch(stock_prices, metrics_date, back_period_weeks)
    logger.info(f"Computed {len(stock_metrics_batch)} stock metrics for {metrics_date}")

    # Save to database
    async with conn.get_db_session() as db_session:
        await save_stock_metrics(db_session, stock_metrics_batch, metrics_date.date())

    return stock_metrics_batch


async def load_stock_metrics_batch(metrics_date: datetime) -> list[StockMetrics]:
    """
    Load stock metrics from the database for a specific metrics date.
    Returns a list of StockMetrics objects, or None if not found.
    """
    async with conn.get_db_session() as db_session:
        stock_metrics_batch = await load_stock_metrics(db_session, metrics_date.date())

    return stock_metrics_batch


async def list_metrics_dates() -> list[datetime]:
    async with conn.get_db_session() as db_session:
        return await queries.list_metrics_dates(db_session)


async def has_metrics(metrics_date: datetime) -> bool:
    """Check if metrics exist for a given date."""
    async with conn.get_db_session() as db_session:
        return await has_metrics_for_date(db_session, metrics_date.date())
