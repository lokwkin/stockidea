"""Load stock symbols from various data sources."""

import bisect
from datetime import date
import time
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


def get_stock_price(symbol: str, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Get stock price for a specific date using binary search for O(log n) performance.

    Uses Python's bisect module (standard library) for efficient binary search.
    Note: get_stock_price_history already has caching via fmp.fetch_stock_prices.
    """
    stock_prices = get_stock_price_history(symbol)

    if not stock_prices:
        raise ValueError(f"No price data available for symbol: {symbol}")

    # stock_prices is sorted by date, from newest to oldest (descending)
    # Use bisect module: reverse the dates list to get ascending order for bisect
    # Extract dates and reverse them for bisect (which expects ascending order)
    dates_reversed = [price.date for price in reversed(stock_prices)]
    prices_reversed = list(reversed(stock_prices))

    # Use bisect_left to find insertion point in ascending-sorted list
    # bisect_left returns the leftmost position where target_date would be inserted
    idx = bisect.bisect_left(dates_reversed, target_date)

    # Check for exact match
    if idx < len(dates_reversed) and dates_reversed[idx] == target_date:
        return prices_reversed[idx]

    # If exact match not found
    if nearest:
        if idx > 0:
            # idx points to first date >= target_date
            # So dates_reversed[idx-1] is the last date < target_date
            # This is the nearest date <= target_date (since we already checked for ==)
            print(f"Using nearest date: {target_date} -> {prices_reversed[idx - 1].date}")
            return prices_reversed[idx - 1]
        elif idx == 0 and stock_prices:
            # idx == 0 means target_date is older than all dates
            # Return the oldest date (first in reversed list)
            return prices_reversed[0]

    raise ValueError(
        f"Stock price not found for symbol: {symbol} on date: {target_date}"
    )
