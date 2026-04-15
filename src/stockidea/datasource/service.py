"""High-level datasource orchestration for fetching and refreshing market data."""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.datasource import constituent, fmp
from stockidea.datasource.database import conn, queries
from stockidea.types import StockIndex

logger = logging.getLogger(__name__)

SUPPORTED_INDEXES = [StockIndex.SP500, StockIndex.NASDAQ]


async def fetch_constituent_changes(db_session: AsyncSession, index: StockIndex) -> int:
    """Fetch constituent change history from FMP and store in database.

    Returns the number of constituent changes fetched.
    """
    changes = await fmp.fetch_historical_constituent(index)
    await queries.save_constituent_changes(db_session, index, changes)
    logger.info(f"Fetched {len(changes)} constituent changes for {index.value}")
    return len(changes)


async def fetch_index_prices(db_session: AsyncSession, index: StockIndex) -> int:
    """Fetch index price history from FMP and store in database.

    Returns the number of price records saved.
    """
    fmp_prices = await fmp.fetch_index_prices(index)
    await queries.save_index_prices(db_session, index, fmp_prices)
    logger.info(f"Fetched {len(fmp_prices)} index prices for {index.value}")
    return len(fmp_prices)


async def fetch_stock_prices(
    db_session: AsyncSession,
    index: StockIndex,
) -> dict[str, int]:
    """Fetch stock prices for all current constituents of an index sequentially.

    Skips symbols that are already fresh (fetched today).

    Args:
        db_session: Database session
        index: Stock index to fetch constituents from

    Returns:
        Dict mapping symbol to number of prices fetched (0 means already fresh or failed)
    """
    today = date.today()
    symbols = await constituent.get_constituent_at(db_session, index, today)
    logger.info(f"Fetching prices for {len(symbols)} constituents of {index.value}")

    results: dict[str, int] = {}

    for symbol in symbols:
        try:
            if await queries.is_data_fresh(db_session, symbol):
                results[symbol] = 0
                continue
            fmp_prices = await fmp.fetch_stock_prices(symbol)
            await queries.save_stock_prices(db_session, symbol, fmp_prices)
            results[symbol] = len(fmp_prices)
            logger.info(f"Fetched {len(fmp_prices)} prices for {symbol}")
        except Exception as e:
            logger.error(f"Failed to fetch prices for {symbol}: {e}")
            results[symbol] = 0

    fetched_count = sum(1 for v in results.values() if v > 0)
    skipped_count = sum(1 for v in results.values() if v == 0)
    logger.info(
        f"{index.value}: {fetched_count} fetched, {skipped_count} already fresh/failed"
    )
    return results


async def refresh_all() -> None:
    """Refresh all market data: constituents, index prices, and stock prices.

    Called on app startup and available via CLI. Skips anything already fetched today.
    """
    logger.info("Starting data refresh for all supported indexes...")

    async with conn.get_db_session() as db_session:
        for index in SUPPORTED_INDEXES:
            # 1. Refresh constituent lists
            if not await queries.is_constituent_data_fresh(db_session, index):
                logger.info(f"Refreshing constituent list for {index.value}")
                await fetch_constituent_changes(db_session, index)
            else:
                logger.info(f"Constituent list for {index.value} is fresh")

            # 2. Refresh index prices
            if not await queries.is_data_fresh(db_session, index.value):
                logger.info(f"Refreshing index prices for {index.value}")
                await fetch_index_prices(db_session, index)
            else:
                logger.info(f"Index prices for {index.value} are fresh")

            # 3. Refresh stock prices for all constituents
            logger.info(f"Checking stock prices for {index.value} constituents...")
            await fetch_stock_prices(db_session, index)

    logger.info("Data refresh complete")
