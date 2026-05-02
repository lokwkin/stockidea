from datetime import date
import logging
import httpx

from stockidea.constants import FMP_API_KEY, FMP_BASE_URL
from stockidea.types import (
    ConstituentChange,
    FMPAdjustedStockPrice,
    FMPFullPrice,
    StockIndex,
)

logger = logging.getLogger(__name__)


def _require_api_key() -> str:
    if not FMP_API_KEY:
        raise ValueError(
            "FMP_API_KEY not found in environment variables. Check your .env file."
        )
    return FMP_API_KEY


async def fetch_index_prices(
    index: StockIndex, from_date: date | None = None
) -> list[FMPFullPrice]:
    """Fetch unadjusted OHLCV for an index from FMP's /historical-price-eod/full.

    Indices are not on FMP's dividend-adjusted endpoint (returns 402), but the
    full endpoint works and returns OHLC — needed so we can use Monday open /
    Friday close prices for the baseline.
    """
    api_key = _require_api_key()
    match index:
        case StockIndex.SP500:
            symbol = "^GSPC"
        case StockIndex.NASDAQ:
            symbol = "^IXIC"
        case _:
            raise ValueError(f"Unsupported index: {index}")
    from_str = from_date.isoformat() if from_date else "2011-01-01"
    logger.info(f"Fetching index prices for {index.value} ({symbol}) from {from_str}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/historical-price-eod/full",
            params={"symbol": symbol.upper(), "apikey": api_key, "from": from_str},
        )
        response.raise_for_status()
        data: list[dict] = response.json()
        return [FMPFullPrice.model_validate(item) for item in data]


async def fetch_stock_prices(
    symbol: str, from_date: date | None = None
) -> list[FMPAdjustedStockPrice]:
    api_key = _require_api_key()
    from_str = from_date.isoformat() if from_date else "2011-01-01"
    logger.info(f"Fetching stock prices for {symbol} from {from_str}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/historical-price-eod/dividend-adjusted",
            params={"symbol": symbol.upper(), "apikey": api_key, "from": from_str},
        )
        response.raise_for_status()

        data: list[dict] = response.json()

        prices = [FMPAdjustedStockPrice.model_validate(item) for item in data]
        # Sort by date, from newest to oldest
        return sorted(prices, key=lambda x: x.date, reverse=True)


async def fetch_sma(
    symbol: str, period_length: int, from_date: date | None = None
) -> list[tuple[date, float]]:
    """Fetch daily SMA series from FMP. Returns list of (date, sma) sorted ascending."""
    api_key = _require_api_key()
    from_str = from_date.isoformat() if from_date else "2011-01-01"
    logger.info(f"Fetching SMA({period_length}) for {symbol.upper()} from {from_str}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/technical-indicators/sma",
            params={
                "symbol": symbol.upper(),
                "periodLength": period_length,
                "timeframe": "1day",
                "apikey": api_key,
                "from": from_str,
            },
        )
        response.raise_for_status()
        data: list[dict] = response.json()

    rows: list[tuple[date, float]] = []
    for item in data:
        raw_date = item.get("date")
        raw_sma = item.get("sma")
        if not raw_date or raw_sma is None:
            continue
        # FMP returns timestamps like "2024-01-15 00:00:00" — take the date part
        date_str = raw_date.split(" ")[0]
        rows.append((date.fromisoformat(date_str), float(raw_sma)))
    rows.sort(key=lambda r: r[0])
    return rows


async def fetch_company_profile(symbol: str) -> dict | None:
    """Fetch FMP company profile (description, industry, sector, ceo, etc.). Returns None if unknown."""
    api_key = _require_api_key()
    logger.info(f"Fetching company profile for {symbol}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/profile",
            params={"symbol": symbol.upper(), "apikey": api_key},
        )
        response.raise_for_status()
        data: list[dict] = response.json()
        return data[0] if data else None


async def fetch_stock_peers(symbol: str) -> list[str]:
    """Fetch peer/competitor symbols for a given stock. Returns [] if none."""
    api_key = _require_api_key()
    logger.info(f"Fetching stock peers for {symbol}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/stock-peers",
            params={"symbol": symbol.upper(), "apikey": api_key},
        )
        response.raise_for_status()
        data: list[dict] = response.json()
        # FMP returns a list of objects with a `symbol` field for each peer
        return [item["symbol"] for item in data if "symbol" in item]


async def fetch_historical_constituent(index: StockIndex) -> list[ConstituentChange]:
    api_key = _require_api_key()
    logger.info(f"Fetching historical constituent for {index.value}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FMP_BASE_URL}/stable/historical-{index.value}-constituent",
            params={"apikey": api_key},
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
