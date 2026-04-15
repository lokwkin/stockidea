import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.datasource import fmp
from stockidea.types import StockIndex, StockPrice
from stockidea.datasource.database import queries

logger = logging.getLogger(__name__)


async def get_index_prices(
    db_session: AsyncSession, index: StockIndex, from_date: date, to_date: date
) -> list[StockPrice]:
    await _ensure_index_data_fresh(db_session, index)
    prices = await queries.get_prices_by_date_range(
        db_session, index.value, from_date, to_date
    )
    return prices


async def get_index_price_at_date(
    db_session: AsyncSession,
    index: StockIndex,
    target_date: date,
    nearest: bool = False,
) -> StockPrice:
    await _ensure_index_data_fresh(db_session, index)
    return await queries.get_price_by_date(
        db_session, index.value, target_date, nearest
    )


async def get_stock_price_history(
    db_session: AsyncSession, symbol: str, from_date: date, to_date: date
) -> list[StockPrice]:
    await _ensure_stock_data_fresh(db_session, symbol)
    return await queries.get_prices_by_date_range(
        db_session, symbol, from_date, to_date
    )


async def get_stock_price_at_date(
    db_session: AsyncSession, symbol: str, target_date: date, nearest: bool = False
) -> StockPrice:
    await _ensure_stock_data_fresh(db_session, symbol)
    return await queries.get_price_by_date(db_session, symbol, target_date, nearest)


async def _ensure_stock_data_fresh(db_session: AsyncSession, symbol: str) -> None:
    if not await queries.is_data_fresh(db_session, symbol):
        fmp_prices = await fmp.fetch_stock_prices(symbol)
        await queries.save_stock_prices(db_session, symbol, fmp_prices)


async def _ensure_index_data_fresh(db_session: AsyncSession, index: StockIndex) -> None:
    if not await queries.is_data_fresh(db_session, index.value):
        fmp_prices = await fmp.fetch_index_prices(index)
        await queries.save_index_prices(db_session, index, fmp_prices)
