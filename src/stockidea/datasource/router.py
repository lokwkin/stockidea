"""API routes for datasource operations."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn
from stockidea.types import StockIndex

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
