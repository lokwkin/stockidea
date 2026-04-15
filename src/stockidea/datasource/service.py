"""Unified datasource service — single public interface for all market data operations.

Provides:
- Ensure-fresh helpers (check freshness → fetch from FMP → save to DB)
- Data retrieval functions (ensure fresh + query)
- Batch refresh orchestration (CLI / startup)
"""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.datasource import fmp
from stockidea.datasource.database import conn, queries
from stockidea.types import ConstituentChange, StockIndex, StockPrice

logger = logging.getLogger(__name__)

SUPPORTED_INDEXES = [StockIndex.SP500, StockIndex.NASDAQ]


# =============================================================================
# Ensure-fresh helpers
# =============================================================================


async def ensure_stock_prices_fresh(db_session: AsyncSession, symbol: str) -> None:
    """Ensure stock price data for a symbol is fresh, fetching from FMP if stale."""
    if not await queries.is_data_fresh(db_session, symbol):
        fmp_prices = await fmp.fetch_stock_prices(symbol)
        await queries.save_stock_prices(db_session, symbol, fmp_prices)


async def ensure_index_prices_fresh(
    db_session: AsyncSession, index: StockIndex
) -> None:
    """Ensure index price data is fresh, fetching from FMP if stale."""
    if not await queries.is_data_fresh(db_session, index.value):
        fmp_prices = await fmp.fetch_index_prices(index)
        await queries.save_index_prices(db_session, index, fmp_prices)


async def ensure_constituent_data_fresh(
    db_session: AsyncSession, index: StockIndex
) -> list[ConstituentChange]:
    """Ensure constituent data is fresh, fetching from FMP if stale. Returns changes."""
    cached = await queries.load_constituent_changes(db_session, index)
    if cached is not None:
        return cached
    changes = await fmp.fetch_historical_constituent(index)
    await queries.save_constituent_changes(db_session, index, changes)
    return changes


# =============================================================================
# Data retrieval (ensure fresh + query)
# =============================================================================


async def get_index_prices(
    db_session: AsyncSession, index: StockIndex, from_date: date, to_date: date
) -> list[StockPrice]:
    """Get index prices for a date range, fetching from FMP if stale."""
    await ensure_index_prices_fresh(db_session, index)
    return await queries.get_prices_by_date_range(
        db_session, index.value, from_date, to_date
    )


async def get_index_price_at_date(
    db_session: AsyncSession,
    index: StockIndex,
    target_date: date,
    nearest: bool = False,
) -> StockPrice:
    """Get index price at a specific date, fetching from FMP if stale."""
    await ensure_index_prices_fresh(db_session, index)
    return await queries.get_price_by_date(
        db_session, index.value, target_date, nearest
    )


async def get_stock_price_history(
    db_session: AsyncSession, symbol: str, from_date: date, to_date: date
) -> list[StockPrice]:
    """Get stock price history for a date range, fetching from FMP if stale."""
    await ensure_stock_prices_fresh(db_session, symbol)
    return await queries.get_prices_by_date_range(
        db_session, symbol, from_date, to_date
    )


async def get_stock_price_at_date(
    db_session: AsyncSession, symbol: str, target_date: date, nearest: bool = False
) -> StockPrice:
    """Get stock price at a specific date, fetching from FMP if stale."""
    await ensure_stock_prices_fresh(db_session, symbol)
    return await queries.get_price_by_date(db_session, symbol, target_date, nearest)


async def get_constituent_at(
    db_session: AsyncSession, index: StockIndex, target_date: date
) -> list[str]:
    """Get the constituent symbols of the index at the target date.

    Loads constituent change history and reconstructs membership at the given date.
    """
    changes = await ensure_constituent_data_fresh(db_session, index)
    symbols: set[str] = set()
    for change in changes:
        if change.date > target_date:
            break
        if change.removed_symbol:
            symbols.discard(change.removed_symbol)
        if change.added_symbol:
            symbols.add(change.added_symbol)
    return sorted(symbols)


# =============================================================================
# Batch fetch (CLI / startup)
# =============================================================================


async def fetch_constituent_changes(
    db_session: AsyncSession, index: StockIndex
) -> int:
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

    Returns:
        Dict mapping symbol to number of prices fetched (0 means already fresh or failed)
    """
    today = date.today()
    symbols = await get_constituent_at(db_session, index, today)
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
