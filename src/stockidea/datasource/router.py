"""API routes for datasource operations."""

import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from stockidea.datasource import fmp
from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn
from stockidea.types import StockIndex, StockPrice

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/snp500")
async def get_snp500_prices() -> list[dict]:
    """Fetch and return S&P 500 historical price data."""
    async with conn.get_db_session() as db_session:
        try:
            prices = await datasource_service.get_index_prices(
                db_session,
                StockIndex.SP500,
                datetime.now() - timedelta(weeks=700),
                datetime.now(),
            )
            return [price.model_dump() for price in prices]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch S&P 500 data: {str(e)}"
            )


@router.get("/stocks/{symbol}/profile")
async def get_stock_profile(symbol: str) -> dict:
    """Return FMP company profile + peer list for a stock symbol (live, not cached)."""
    sym = symbol.upper()
    profile_task = asyncio.create_task(fmp.fetch_company_profile(sym))
    peers_task = asyncio.create_task(fmp.fetch_stock_peers(sym))

    profile: dict | None
    peers: list[str]
    try:
        profile = await profile_task
    except Exception as e:
        logger.warning(f"Failed to fetch FMP profile for {sym}: {e}")
        profile = None
    try:
        peers = await peers_task
    except Exception as e:
        logger.warning(f"Failed to fetch FMP peers for {sym}: {e}")
        peers = []

    if profile is None and not peers:
        raise HTTPException(status_code=404, detail=f"No profile data found for {sym}")

    return {"symbol": sym, "profile": profile, "peers": peers}


@router.get("/stocks/{symbol}/prices")
async def get_stock_prices(
    symbol: str,
    from_date: str = Query(
        default=None, alias="from", description="Start date YYYY-MM-DD"
    ),
    to_date: str = Query(default=None, alias="to", description="End date YYYY-MM-DD"),
) -> list[StockPrice]:
    """Return daily price history for a stock symbol."""
    to_dt = (
        datetime.strptime(to_date, "%Y-%m-%d").date()
        if to_date
        else datetime.now().date()
    )
    from_dt = (
        datetime.strptime(from_date, "%Y-%m-%d").date()
        if from_date
        else to_dt - timedelta(weeks=156)
    )

    async with conn.get_db_session() as db_session:
        try:
            prices = await datasource_service.get_stock_price_history(
                db_session, symbol.upper(), from_dt, to_dt
            )
            return prices
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch prices for {symbol}: {str(e)}",
            )
