from datetime import date
from stockpick.config import FMP_API_KEY, FMP_BASE_URL
from stockpick.types import ConstituentChange, FMPAdjustedStockPrice, FMPLightPrice, StockIndex
import os
import requests

if not os.getenv("FMP_API_KEY"):
    raise ValueError(
        "FMP_API_KEY not found in environment variables. Check your .env file."
    )


def fetch_index_prices(index: StockIndex) -> list[FMPLightPrice]:
    match index:
        case StockIndex.SP500:
            symbol = "^GSPC"
        case StockIndex.DOWJONES:
            symbol = "^DJI"
        case StockIndex.NASDAQ:
            symbol = "^IXIC"
        case _:
            raise ValueError(f"Invalid index: {index}")
    print(f"Fetching index prices for {index.value} ({symbol})")
    response = requests.get(
        f"{FMP_BASE_URL}/stable/historical-price-eod/light",
        params={"symbol": symbol.upper(), "apikey": FMP_API_KEY, "from": "2011-01-01"},
        timeout=30,
    )
    response.raise_for_status()
    data: list[dict] = response.json()
    return [FMPLightPrice.model_validate(item) for item in data]


def fetch_stock_prices(symbol: str) -> list[FMPAdjustedStockPrice]:
    print(f"Fetching stock prices for {symbol}")
    response = requests.get(
        f"{FMP_BASE_URL}/stable/historical-price-eod/dividend-adjusted",
        params={"symbol": symbol.upper(), "apikey": FMP_API_KEY, "from": "2011-01-01"},
        timeout=30,
    )
    response.raise_for_status()

    data: list[dict] = response.json()

    prices = [FMPAdjustedStockPrice.model_validate(item) for item in data]
    # Sort by date, from newest to oldest
    return sorted(prices, key=lambda x: x.date, reverse=True)


def fetch_historical_constituent(index: StockIndex) -> list[ConstituentChange]:
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

    return changes
