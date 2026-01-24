from datetime import date
import logging
import os
import httpx

from stockidea.config import FMP_API_KEY, FMP_BASE_URL
from stockidea.types import ConstituentChange, FMPAdjustedStockPrice, FMPLightPrice, StockIndex

logger = logging.getLogger(__name__)

if not os.getenv("FMP_API_KEY"):
    raise ValueError(
        "FMP_API_KEY not found in environment variables. Check your .env file."
    )


async def fetch_index_prices(index: StockIndex) -> list[FMPLightPrice]:
    match index:
        case StockIndex.SP500:
            symbol = "^GSPC"
        case StockIndex.DOWJONES:
            symbol = "^DJI"
        case StockIndex.NASDAQ:
            symbol = "^IXIC"
        case _:
            raise ValueError(f"Invalid index: {index}")
    logger.info(f"Fetching index prices for {index.value} ({symbol})")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/historical-price-eod/light",
            params={"symbol": symbol.upper(), "apikey": FMP_API_KEY, "from": "2011-01-01"},
        )
        response.raise_for_status()
        data: list[dict] = response.json()
        return [FMPLightPrice.model_validate(item) for item in data]


async def fetch_stock_prices(symbol: str) -> list[FMPAdjustedStockPrice]:
    logger.info(f"Fetching stock prices for {symbol}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/historical-price-eod/dividend-adjusted",
            params={"symbol": symbol.upper(), "apikey": FMP_API_KEY, "from": "2011-01-01"},
        )
        response.raise_for_status()

        data: list[dict] = response.json()

        prices = [FMPAdjustedStockPrice.model_validate(item) for item in data]
        # Sort by date, from newest to oldest
        return sorted(prices, key=lambda x: x.date, reverse=True)


async def fetch_historical_constituent(index: StockIndex) -> list[ConstituentChange]:
    logger.info(f"Fetching historical constituent for {index.value}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/historical-{index.value}-constituent",
            params={"apikey": FMP_API_KEY},
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
