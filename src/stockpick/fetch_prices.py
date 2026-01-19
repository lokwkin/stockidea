"""Fetch historical stock price data from Financial Modeling Prep API."""

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

from stockpick.config import PROJECT_ROOT

BASE_URL = "https://financialmodelingprep.com/stable/historical-price-eod/light"
# Cache directory at project root level
CACHE_DIR = PROJECT_ROOT / ".cache"


@dataclass
class StockPrice:
    """Represents a single day's stock price data."""

    symbol: str
    date: date
    price: float
    volume: int


def _get_cache_path(symbol: str) -> Path:
    """Get the cache file path for a symbol."""
    return CACHE_DIR / f"{symbol.upper()}.json"


def _load_from_cache(symbol: str) -> list[StockPrice] | None:
    """
    Load cached price data if it was fetched today.

    Returns:
        List of StockPrice if cache is valid, None otherwise
    """
    cache_path = _get_cache_path(symbol)
    if not cache_path.exists():
        return None

    try:
        with open(cache_path) as f:
            cached = json.load(f)

        # Check if cache is from today
        if cached.get("fetch_date") != date.today().isoformat():
            return None

        # Convert cached data back to StockPrice objects
        return [
            StockPrice(
                symbol=item["symbol"],
                date=date.fromisoformat(item["date"]),
                price=item["price"],
                volume=item["volume"],
            )
            for item in cached["prices"]
        ]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_to_cache(symbol: str, prices: list[dict]) -> None:
    """Save price data to cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = _get_cache_path(symbol)

    cached = {
        "fetch_date": date.today().isoformat(),
        "prices": prices,
    }

    with open(cache_path, "w") as f:
        json.dump(cached, f)


def fetch_stock_prices(symbol: str, use_cache: bool = True) -> list[StockPrice]:
    """
    Fetch historical EOD price data for a given stock symbol.

    Uses daily caching - if prices were fetched today, returns cached data.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')
        use_cache: Whether to use cached data (default True)

    Returns:
        List of StockPrice objects sorted by date (most recent first)

    Raises:
        ValueError: If API key is not configured
        requests.RequestException: If API request fails
    """
    # Try to load from cache first
    if use_cache:
        cached_prices = _load_from_cache(symbol)
        if cached_prices is not None:
            return cached_prices

    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError(
            "FMP_API_KEY not found in environment variables. Check your .env file."
        )

    response = requests.get(
        BASE_URL,
        params={"symbol": symbol, "apikey": api_key},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    # Save raw data to cache
    _save_to_cache(symbol, data)

    return [
        StockPrice(
            symbol=item["symbol"],
            date=date.fromisoformat(item["date"]),
            price=item["price"],
            volume=item["volume"],
        )
        for item in data
    ]


def fetch_stock_prices_batch(symbols: list[str], use_cache: bool = True) -> dict[str, list[StockPrice]]:
    """Fetch historical EOD price data for a list of stock symbols."""
    prices = {}
    for symbol in symbols:
        try:
            prices[symbol] = fetch_stock_prices(symbol, use_cache=use_cache)
        except Exception as e:
            print(f"Error fetching stock prices for {symbol}: {e}")
            continue
    return prices
