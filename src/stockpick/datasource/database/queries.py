"""PostgreSQL database implementation for storing price data using SQLAlchemy."""

from datetime import date, datetime, timedelta
import logging

from sqlalchemy import (
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from stockpick.datasource.database.models import DBStockPrice, DBStockPriceMetadata
from stockpick.types import FMPAdjustedStockPrice, FMPLightPrice, StockIndex, StockPrice

logger = logging.getLogger(__name__)


async def save_index_prices(db_session: AsyncSession, index: StockIndex, prices: list[FMPLightPrice]) -> None:
    logger.info(f"Saving index prices for {index.value}")
    # Delete existing entries for this index
    delete_prices_stmt = delete(DBStockPrice).where(DBStockPrice.symbol == index.value)
    delete_metadata_stmt = delete(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == index.value)
    await db_session.execute(delete_prices_stmt)
    await db_session.execute(delete_metadata_stmt)
    await db_session.commit()

    # Insert new entries
    for price in prices:
        price_record = DBStockPrice(
            symbol=index.value, date=date.fromisoformat(price.date), adj_close=price.price, close=price.price, volume=price.volume)
        db_session.add(price_record)

    # Update metadata for this index
    metadata = DBStockPriceMetadata(symbol=index.value, fetched_at=datetime.now())
    db_session.add(metadata)
    await db_session.commit()


async def save_stock_prices(db_session: AsyncSession, symbol: str, prices: list[FMPAdjustedStockPrice]) -> None:

    # Delete existing entries for this symbol
    delete_prices_stmt = delete(DBStockPrice).where(DBStockPrice.symbol == symbol.upper())
    delete_metadata_stmt = delete(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == symbol.upper())
    await db_session.execute(delete_prices_stmt)
    await db_session.execute(delete_metadata_stmt)
    await db_session.commit()

    # Insert new entries
    for price_data in prices:
        price_record = DBStockPrice(
            symbol=symbol.upper(),
            date=date.fromisoformat(price_data.date),
            open=price_data.adjOpen,
            high=price_data.adjHigh,
            low=price_data.adjLow,
            close=price_data.adjClose,
            adj_close=price_data.adjClose,
            volume=price_data.volume,
            created_at=datetime.now(),
        )
        db_session.add(price_record)

    # Update metadata for this symbol
    metadata = DBStockPriceMetadata(
        symbol=symbol.upper(),
        fetched_at=datetime.now(),
    )
    db_session.add(metadata)

    await db_session.commit()


async def is_data_fresh(db_session: AsyncSession, symbol: str) -> bool:
    stmt = select(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == symbol.upper())
    result = await db_session.execute(stmt)
    metadata = result.scalar_one_or_none()
    # if the symbol prices are last fetched more than 1 day ago, return False
    if metadata is None:
        return False

    return metadata.fetched_at > datetime.now() - timedelta(days=1)


async def get_prices_by_date_range(db_session: AsyncSession, symbol: str, from_date: date, to_date: date) -> list[StockPrice]:
    """
    Get the stock prices for a given symbol and date range.
    """
    stmt = select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close).where(DBStockPrice.symbol == symbol.upper()).where(
        DBStockPrice.date >= from_date).where(DBStockPrice.date <= to_date).order_by(DBStockPrice.date.desc())
    result = await db_session.execute(stmt)
    prices = result.all()  # Returns Row objects when selecting multiple columns
    return [StockPrice(
        symbol=price.symbol,
        date=price.date,
        adj_close=price.adj_close
    ) for price in prices]


async def get_price_by_date(db_session: AsyncSession, symbol: str, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Get the stock price for a given symbol and date.
    If nearest is True, and the price is not found for the given date, return the price for the nearest date before the given date.
    """
    stmt = select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close).where(DBStockPrice.symbol == symbol.upper()).where(
        DBStockPrice.date == target_date).order_by(DBStockPrice.date.desc())
    result = await db_session.execute(stmt)
    price = result.first()  # Returns Row object or None when selecting multiple columns
    if price is not None:
        return StockPrice(
            symbol=price.symbol,
            date=price.date,
            adj_close=price.adj_close
        )
    if nearest:
        # Find the price of nearest date we have before the target date
        stmt = select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close).where(DBStockPrice.symbol == symbol.upper()).where(
            DBStockPrice.date < target_date).order_by(DBStockPrice.date.desc()).limit(1)
        result = await db_session.execute(stmt)
        price = result.first()  # Returns Row object or None when selecting multiple columns
        if price is not None:
            return StockPrice(
                symbol=price.symbol,
                date=price.date,
                adj_close=price.adj_close
            )

    raise ValueError(f"No price data available for symbol: {symbol} on date: {target_date}")
