import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging
from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import uvicorn

from stockidea.indicators import (
    service as indicators_service,
    calculator as indicators_calculator,
)
from stockidea.rule_engine import compile_rule, extract_involved_keys
from stockidea.backtest.backtester import Backtester
from stockidea.types import (
    EnqueuedJob,
    BacktestConfig,
    BacktestJob,
    StockIndex,
    StrategyCreate,
    StrategySummary,
    StrategyDetail,
)
from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn, queries
from typing import Optional


logger = logging.getLogger(__name__)


async def _worker_loop() -> None:
    """Background worker that processes pending backtest jobs."""
    logger.info("Backtest worker started")
    while True:
        try:
            async with conn.get_db_session() as db_session:
                job = await queries.claim_next_pending_job(db_session)

            if job is None:
                await asyncio.sleep(2)
                continue

            logger.info(f"Processing backtest job {job.id}")
            try:
                config = BacktestConfig.model_validate_json(job.config_json)
                async with conn.get_db_session() as db_session:
                    backtester = Backtester(
                        db_session=db_session,
                        max_stocks=config.max_stocks,
                        rebalance_interval_weeks=config.rebalance_interval_weeks,
                        date_start=config.date_start,
                        date_end=config.date_end,
                        rule_func=compile_rule(config.rule),
                        rule_raw=config.rule,
                        from_index=config.index,
                        baseline_index=StockIndex.SP500,
                    )
                    backtest_result = await backtester.backtest()
                    backtest_id = await queries.save_backtest_result(
                        db_session, backtest_result
                    )

                async with conn.get_db_session() as db_session:
                    await queries.mark_job_completed(db_session, job.id, backtest_id)

                logger.info(f"Job {job.id} completed → backtest {backtest_id}")

            except Exception as exc:
                logger.exception(f"Job {job.id} failed: {exc}")
                async with conn.get_db_session() as db_session:
                    await queries.mark_job_failed(db_session, job.id, str(exc))

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception(f"Worker loop error: {exc}")
            await asyncio.sleep(5)

    logger.info("Backtest worker stopped")


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

    worker_task = asyncio.create_task(_worker_loop())
    yield
    worker_task.cancel()
    refresh_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="StockPick API", version="0.1.0", lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/backtests")
async def list_backtests() -> list[dict]:
    """Return list of available backtests from database."""
    async with conn.get_db_session() as db_session:
        backtests = await queries.list_backtests(db_session)
        return backtests


@app.get("/backtests/{backtest_id}")
async def get_backtest(backtest_id: UUID) -> dict:
    """Return the full JSON content of a backtest by ID."""
    async with conn.get_db_session() as db_session:
        backtest_result = await queries.get_backtest_by_id(db_session, backtest_id)
        if backtest_result is None:
            raise HTTPException(
                status_code=404, detail=f"Backtest not found: {backtest_id}"
            )
        return backtest_result.model_dump()


@app.get("/indicators")
async def list_analysis() -> list[str]:
    async with conn.get_db_session() as db_session:
        dates = await indicators_service.list_indicator_dates(db_session)
    return [date.strftime("%Y-%m-%d") for date in dates]


@app.get("/indicators/{date}/")
async def get_analysis(
    date: str, rule: Optional[str] = None, index: StockIndex = StockIndex.SP500
) -> dict:

    indicators_date = datetime.strptime(date, "%Y-%m-%d")

    async with conn.get_db_session() as db_session:
        # Get the symbols of the constituent
        symbols = await datasource_service.get_constituent_at(
            db_session, index, indicators_date.date()
        )
        stock_indicators_batch = await indicators_service.get_stock_indicators_batch(
            db_session,
            symbols=symbols,
            indicators_date=indicators_date,
            back_period_weeks=52,
        )

    # Apply rule if provided
    if rule:
        try:
            rule_func = compile_rule(rule)
            # Filter using the rule (no max_stocks limit for API)
            stock_indicators_batch = [
                stock_indicator
                for stock_indicator in stock_indicators_batch
                if rule_func(stock_indicator)
            ]
            # Sort by rising stability score
            stock_indicators_batch = (
                indicators_calculator.rank_by_rising_stability_score(
                    stock_indicators_batch
                )
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    return {
        "date": indicators_date.strftime("%Y-%m-%d"),
        "data": [
            stock_indicator.model_dump() for stock_indicator in stock_indicators_batch
        ],
    }


@app.post("/backtest")
async def backtest(backtest_config: BacktestConfig) -> EnqueuedJob:
    """
    Enqueue a backtest job and return the job ID for status polling.
    """
    # Populate involved_keys from rule if not provided
    if not backtest_config.involved_keys:
        backtest_config.involved_keys = extract_involved_keys(backtest_config.rule)

    # Validate rule before enqueuing
    try:
        compile_rule(backtest_config.rule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    async with conn.get_db_session() as db_session:
        job_id = await queries.create_backtest_job(db_session, backtest_config)

    return EnqueuedJob(job_id=job_id, status="pending")


@app.get("/jobs/{job_id}")
async def get_job(job_id: UUID) -> BacktestJob:
    """Return the status of a backtest job."""
    async with conn.get_db_session() as db_session:
        job = await queries.get_job_by_id(db_session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@app.get("/jobs")
async def list_jobs() -> list[BacktestJob]:
    """Return the most recent backtest jobs."""
    async with conn.get_db_session() as db_session:
        return await queries.list_recent_jobs(db_session)


@app.get("/snp500")
async def get_snp500_prices() -> list[dict]:
    """
    Fetch and return S&P 500 historical price data.

    Returns a list of price data points with date and price fields.
    """
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


# =============================================================================
# Strategy Endpoints
# =============================================================================


@app.get("/strategies")
async def list_strategies() -> list[StrategySummary]:
    """List all strategies."""
    async with conn.get_db_session() as db_session:
        return await queries.list_strategies(db_session)


@app.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: UUID) -> StrategyDetail:
    """Get a strategy with its messages and linked backtests."""
    async with conn.get_db_session() as db_session:
        strategy = await queries.get_strategy_by_id(db_session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@app.post("/strategies")
async def create_strategy(request: StrategyCreate):
    """Create a new strategy and start the first agent run via SSE."""
    from datetime import date, timedelta

    from stockidea.agent.agent import run_agent_stream

    end = request.date_end or date.today()
    start = request.date_start or (end - timedelta(days=365 * 3))

    # Generate a name from the first ~50 chars of the instruction
    name = request.instruction[:50].strip()
    if len(request.instruction) > 50:
        name += "..."

    async with conn.get_db_session() as db_session:
        strategy_id = await queries.create_strategy(
            db_session, request, name=name, date_start=start, date_end=end
        )

    # Save user message
    async with conn.get_db_session() as db_session:
        await queries.add_strategy_message(
            db_session,
            strategy_id,
            role="user",
            content_json=json.dumps({"text": request.instruction}),
        )

    strategy_id_str = str(strategy_id)

    async def event_stream():
        # First emit the strategy ID so the frontend knows where to navigate
        yield f"event: strategy_created\ndata: {json.dumps({'strategy_id': strategy_id_str})}\n\n"

        async with conn.get_db_session() as db_session:
            await queries.update_strategy_status(db_session, strategy_id, "running")

        agent_events: list[dict] = []
        llm_history: str | None = None
        try:
            async for event in run_agent_stream(
                request.instruction,
                request.model,
                date_start=start,
                date_end=end,
                strategy_id=strategy_id_str,
            ):
                event_type = event["event"]

                if event_type == "done":
                    llm_history = event["data"].get("llm_history")
                    # Don't include llm_history in the SSE data sent to frontend
                    yield f"event: done\ndata: {json.dumps({})}\n\n"
                else:
                    agent_events.append(event)
                    data = json.dumps(event["data"])
                    yield f"event: {event_type}\ndata: {data}\n\n"

        except Exception as e:
            logger.exception(f"Agent stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            async with conn.get_db_session() as db_session:
                await queries.update_strategy_status(db_session, strategy_id, "failed")
            return

        # Persist agent events as a message
        async with conn.get_db_session() as db_session:
            await queries.add_strategy_message(
                db_session,
                strategy_id,
                role="assistant",
                content_json=json.dumps(agent_events),
            )
            if llm_history:
                await queries.update_strategy_llm_history(
                    db_session, strategy_id, llm_history
                )
            await queries.update_strategy_status(db_session, strategy_id, "idle")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class FollowUpRequest(BaseModel):
    instruction: str


@app.post("/strategies/{strategy_id}/messages")
async def send_strategy_message(strategy_id: UUID, request: FollowUpRequest):
    """Send a follow-up message to a strategy and run the agent with prior context."""

    from stockidea.agent.agent import run_agent_stream

    # Load strategy and its LLM history
    async with conn.get_db_session() as db_session:
        strategy = await queries.get_strategy_by_id(db_session, strategy_id)

    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status == "running":
        raise HTTPException(status_code=409, detail="Strategy is already running")

    # Parse LLM history for continuation
    history: list[dict] | None = None
    if strategy.llm_history_json:
        try:
            history = json.loads(strategy.llm_history_json)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM history for strategy {strategy_id}")

    # Save user follow-up message
    async with conn.get_db_session() as db_session:
        await queries.add_strategy_message(
            db_session,
            strategy_id,
            role="user",
            content_json=json.dumps({"text": request.instruction}),
        )

    strategy_id_str = str(strategy_id)

    async def event_stream():
        async with conn.get_db_session() as db_session:
            await queries.update_strategy_status(db_session, strategy_id, "running")

        agent_events: list[dict] = []
        llm_history_result: str | None = None
        try:
            async for event in run_agent_stream(
                request.instruction,
                strategy.model,
                date_start=strategy.date_start,
                date_end=strategy.date_end,
                history=history,
                strategy_id=strategy_id_str,
            ):
                event_type = event["event"]

                if event_type == "done":
                    llm_history_result = event["data"].get("llm_history")
                    yield f"event: done\ndata: {json.dumps({})}\n\n"
                else:
                    agent_events.append(event)
                    data = json.dumps(event["data"])
                    yield f"event: {event_type}\ndata: {data}\n\n"

        except Exception as e:
            logger.exception(f"Agent stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            async with conn.get_db_session() as db_session:
                await queries.update_strategy_status(db_session, strategy_id, "failed")
            return

        # Persist agent events as a message
        async with conn.get_db_session() as db_session:
            await queries.add_strategy_message(
                db_session,
                strategy_id,
                role="assistant",
                content_json=json.dumps(agent_events),
            )
            if llm_history_result:
                await queries.update_strategy_llm_history(
                    db_session, strategy_id, llm_history_result
                )
            await queries.update_strategy_status(db_session, strategy_id, "idle")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: UUID):
    """Delete a strategy and all its messages."""
    async with conn.get_db_session() as db_session:
        deleted = await queries.delete_strategy(db_session, strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"status": "deleted"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
