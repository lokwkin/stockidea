from datetime import date
import json
import time
from typing import Any
from stockpick.config import CACHE_DIR, FMP_API_KEY, FMP_BASE_URL
from stockpick.types import ConstituentChange, StockIndex, StockPrice
import os
import requests

if not os.getenv("FMP_API_KEY"):
    raise ValueError(
        "FMP_API_KEY not found in environment variables. Check your .env file."
    )


def fetch_stock_prices(symbol: str) -> list[StockPrice]:
    cached = _load_from_cache(f"price_{symbol}")
    if cached is not None:
        return [StockPrice.model_validate(price) for price in cached]

    print(f"Fetching stock prices for {symbol}")
    response = requests.get(
        f"{FMP_BASE_URL}/stable/historical-price-eod/light",
        params={"symbol": symbol, "apikey": FMP_API_KEY, "from": "2011-01-01"},
        timeout=30,
    )
    response.raise_for_status()

    data: list[dict] = response.json()

    prices = sorted([
        StockPrice(
            symbol=item["symbol"],
            date=date.fromisoformat(item["date"]),
            price=item["price"],
            volume=item["volume"],
        )
        for item in data
    ], key=lambda x: x.date, reverse=True)  # sort by date, from newest to oldest

    _save_to_cache(f"price_{symbol.upper()}", [price.model_dump(mode="json") for price in prices])

    return prices


def fetch_historical_constituent(index: StockIndex) -> list[ConstituentChange]:

    cached = _load_from_cache(f"historical-{index.value}-constituent")
    if cached is not None:
        return [ConstituentChange.model_validate(change) for change in cached]

    print(f"Fetching historical constituent for {index.value}")
    response = requests.get(
        f"{FMP_BASE_URL}/stable/historical-{index.value}-constituent",
        params={"apikey": FMP_API_KEY},
        timeout=30,
    )
    response.raise_for_status()

    data: list[dict] = response.json()

    changes = sorted(
        [
            ConstituentChange(
                date=date.fromisoformat(change["date"]),
                added_symbol=change.get("symbol", ""),
                removed_symbol=change.get("removedTicker", ""),
            )
            for change in data
        ],
        key=lambda x: x.date,
    )

    _save_to_cache(f"historical-{index.value}-constituent", [change.model_dump(mode="json") for change in changes])

    return changes


PRICE_CACHE: dict[str, list[StockPrice]] = {}


def _save_to_cache(key: str, data: Any) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{key}.json"

    with open(cache_path, "w") as f:
        json.dump({
            "cache_date": date.today().isoformat(),  # TTL is 1 day
            "data": data,
        }, f)

    PRICE_CACHE[key] = data


def _load_from_cache(key: str) -> Any | None:
    if key in PRICE_CACHE:
        return PRICE_CACHE[key]

    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{key}.json"

    if not cache_path.exists():
        return None

    with open(cache_path, "r") as f:
        cached = json.load(f)

    if cached.get("cache_date") != date.today().isoformat():
        return None

    return cached.get("data")
