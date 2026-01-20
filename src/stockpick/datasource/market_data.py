"""Load stock symbols from various data sources."""

from datetime import date
from stockpick.datasource import fmp
from stockpick.types import StockIndex, StockPrice


def get_constituent(index: StockIndex, target_date: date) -> list[str]:
    # Build the set of symbols by processing each change chronologically
    symbols = set()

    for change in fmp.fetch_historical_constituent(index):
        # Stop processing if we've passed the target date
        if change.date > target_date:
            break

        # Remove the old symbol first (if it exists)
        if change.removed_symbol:
            symbols.discard(change.removed_symbol)

        # Add the new symbol
        if change.added_symbol:
            symbols.add(change.added_symbol)

    # Return sorted list
    return sorted(symbols)


def get_stock_price_histories(symbols: list[str]) -> dict[str, list[StockPrice]]:
    prices = {}
    for symbol in symbols:
        try:
            prices[symbol] = get_stock_price_history(symbol)
        except Exception as e:
            print(f"Error fetching stock prices for {symbol}: {e}")
            continue
    return prices


def get_stock_price_history(symbol: str) -> list[StockPrice]:
    return fmp.fetch_stock_prices(symbol)


def get_stock_price(symbol: str, date: date, nearest: bool = False) -> StockPrice:
    stock_prices = get_stock_price_history(symbol)

    # stock_prices is sorted by date, from newest to oldest
    price = next((price for price in stock_prices if price.date == date), None)
    if price is not None:
        return price

    if nearest:
        price = next((price for price in stock_prices if price.date < date), None)
        if price is not None:
            return price

    raise ValueError(
        f"Stock price not found for symbol: {symbol} on date: {date}"
    )
