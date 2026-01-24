import asyncio
import logging
from datetime import date

from stockpick.datasource import fmp
from stockpick.types import StockIndex, StockPrice
from stockpick.datasource.database import conn, queries

logger = logging.getLogger(__name__)


async def get_index_prices(index: StockIndex, from_date: date, to_date: date) -> list[StockPrice]:
    """
    Return the index prices for a given index and date range.
    """
    async with conn.get_db_session() as db_session:
        await _ensure_index_data_fresh(db_session, index)
        prices = await queries.get_prices_by_date_range(db_session, index.value, from_date, to_date)
        return prices


async def get_index_price_at_date(index: StockIndex, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Return the index price for a given index and date.
    """
    async with conn.get_db_session() as db_session:
        await _ensure_index_data_fresh(db_session, index)
        return await queries.get_price_by_date(db_session, index.value, target_date, nearest)


async def get_stock_price_batch_histories(symbols: list[str], from_date: date, to_date: date) -> dict[str, list[StockPrice]]:
    """
    Return the stock price history for a given list of symbols and date range.
    """

    async def fetch_with_error_handling(semaphore: asyncio.Semaphore, symbol: str) -> tuple[str, list[StockPrice] | None]:
        async with semaphore:
            try:
                # If the data is not fresh, fetch it from the API and update the database
                prices = await get_stock_price_history(symbol, from_date, to_date)
                return (symbol, prices)
            except Exception as e:
                logger.error(f"Error fetching stock prices for {symbol}: {e}")
                return (symbol, None)

    semaphore = asyncio.Semaphore(30)
    tasks = [fetch_with_error_handling(semaphore, symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)

    prices_by_symbol = {}
    for symbol, prices in results:
        if prices is not None:
            prices_by_symbol[symbol] = prices

    return prices_by_symbol


async def get_stock_price_history(symbol: str, from_date: date, to_date: date) -> list[StockPrice]:
    """
    Return the stock price history for a given symbol and date range.
    """

    async with conn.get_db_session() as db_session:
        await _ensure_stock_data_fresh(db_session, symbol)

        # Get the data from the database
        return await queries.get_prices_by_date_range(db_session, symbol, from_date, to_date)


async def get_stock_price_at_date(symbol: str, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Return the stock price for a given symbol and date.
    """

    async with conn.get_db_session() as db_session:
        await _ensure_stock_data_fresh(db_session, symbol)

        return await queries.get_price_by_date(db_session, symbol, target_date, nearest)


async def _ensure_stock_data_fresh(db_session, symbol: str) -> None:
    if not await queries.is_data_fresh(db_session, symbol):
        fmp_prices = await fmp.fetch_stock_prices(symbol)
        await queries.save_stock_prices(db_session, symbol, fmp_prices)


async def _ensure_index_data_fresh(db_session, index: StockIndex) -> None:
    if not await queries.is_data_fresh(db_session, index.value):
        fmp_prices = await fmp.fetch_index_prices(index)
        await queries.save_index_prices(db_session, index, fmp_prices)
