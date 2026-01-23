from datetime import date

from sqlalchemy.orm.session import Session
from stockpick.datasource import fmp
from stockpick.types import StockIndex, StockPrice
from stockpick.datasource import sqlite


def get_index_prices(index: StockIndex, from_date: date, to_date: date) -> list[StockPrice]:
    """
    Return the index prices for a given index and date range.
    """
    db_session = sqlite.get_db_session()
    _ensure_index_data_fresh(db_session, index)
    prices = sqlite.get_prices_by_date_range(db_session, index.value, from_date, to_date)
    return prices


def get_index_price_at_date(index: StockIndex, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Return the index price for a given index and date.
    """
    db_session = sqlite.get_db_session()
    _ensure_index_data_fresh(db_session, index)
    return sqlite.get_price_by_date(db_session, index.value, target_date, nearest)


def get_stock_price_batch_histories(symbols: list[str], from_date: date, to_date: date) -> dict[str, list[StockPrice]]:
    """
    Return the stock price history for a given list of symbols and date range.
    """

    prices_by_symbol = {}
    for symbol in symbols:
        try:
            # If the data is not fresh, fetch it from the API and update the database
            prices_by_symbol[symbol] = get_stock_price_history(symbol, from_date, to_date)
        except Exception as e:
            print(f"Error fetching stock prices for {symbol}: {e}")
            continue

    return prices_by_symbol


def get_stock_price_history(symbol: str, from_date: date, to_date: date) -> list[StockPrice]:
    """
    Return the stock price history for a given symbol and date range.
    """

    db_session = sqlite.get_db_session()

    _ensure_stock_data_fresh(db_session, symbol)

    # Get the data from the database
    return sqlite.get_prices_by_date_range(db_session, symbol, from_date, to_date)


def get_stock_price_at_date(symbol: str, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Return the stock price for a given symbol and date.
    """

    db_session = sqlite.get_db_session()

    _ensure_stock_data_fresh(db_session, symbol)

    price = sqlite.get_price_by_date(db_session, symbol, target_date, nearest)
    if price is not None:
        return price
    return fmp.fetch_stock_price(symbol, target_date)


def _ensure_stock_data_fresh(db_session: Session, symbol: str) -> None:
    if not sqlite.is_data_fresh(db_session, symbol):
        fmp_prices = fmp.fetch_stock_prices(symbol)
        sqlite.save_stock_prices(db_session, symbol, fmp_prices)


def _ensure_index_data_fresh(db_session: Session, index: StockIndex) -> None:
    if not sqlite.is_data_fresh(db_session, index.value):
        fmp_prices = fmp.fetch_index_prices(index)
        sqlite.save_index_prices(db_session, index, fmp_prices)
