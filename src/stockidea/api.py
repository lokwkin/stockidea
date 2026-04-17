"""FastAPI application — assembles component routers."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from stockidea.datasource import service as datasource_service
from stockidea.datasource.router import router as datasource_router
from stockidea.indicators.router import router as indicators_router
from stockidea.backtest.router import router as backtest_router
from stockidea.agent.router import router as agent_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-refresh market data on startup (runs in background, non-blocking)
    refresh_task = asyncio.create_task(datasource_service.refresh_all())
    refresh_task.add_done_callback(
        lambda t: (
            logger.error(f"Data refresh failed: {t.exception()}")
            if t.exception()
            else None
        )
    )

    yield
    refresh_task.cancel()


app = FastAPI(title="StockPick API", version="0.1.0", lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register component routers
app.include_router(datasource_router)
app.include_router(indicators_router)
app.include_router(backtest_router)
app.include_router(agent_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
