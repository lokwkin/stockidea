import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging
from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException

import uvicorn

from stockidea.analysis import metrics, metrics_calculator
from stockidea.rule_engine import compile_rule, extract_involved_keys
from stockidea.simulation.simulator import Simulator
from stockidea.types import EnqueuedJob, SimulationConfig, SimulationJob, StockIndex
from stockidea.datasource import constituent, market_data
from stockidea.datasource.database import conn, queries
from typing import Optional


logger = logging.getLogger(__name__)


async def _worker_loop() -> None:
    """Background worker that processes pending simulation jobs."""
    logger.info("Simulation worker started")
    while True:
        try:
            async with conn.get_db_session() as db_session:
                job = await queries.claim_next_pending_job(db_session)

            if job is None:
                await asyncio.sleep(2)
                continue

            logger.info(f"Processing simulation job {job.id}")
            try:
                config = SimulationConfig.model_validate_json(job.config_json)
                async with conn.get_db_session() as db_session:
                    simulator = Simulator(
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
                    simulation_result = await simulator.simulate()
                    simulation_id = await queries.save_simulation_result(db_session, simulation_result)

                async with conn.get_db_session() as db_session:
                    await queries.mark_job_completed(db_session, job.id, simulation_id)

                logger.info(f"Job {job.id} completed → simulation {simulation_id}")

            except Exception as exc:
                logger.exception(f"Job {job.id} failed: {exc}")
                async with conn.get_db_session() as db_session:
                    await queries.mark_job_failed(db_session, job.id, str(exc))

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception(f"Worker loop error: {exc}")
            await asyncio.sleep(5)

    logger.info("Simulation worker stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(_worker_loop())
    yield
    worker_task.cancel()
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


@app.get("/simulations")
async def list_simulations() -> list[dict]:
    """Return list of available simulations from database."""
    async with conn.get_db_session() as db_session:
        simulations = await queries.list_simulations(db_session)
        return simulations


@app.get("/simulations/{simulation_id}")
async def get_simulation(simulation_id: UUID) -> dict:
    """Return the full JSON content of a simulation by ID."""
    async with conn.get_db_session() as db_session:
        simulation_result = await queries.get_simulation_by_id(db_session, simulation_id)
        if simulation_result is None:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
        return simulation_result.model_dump()


@app.get("/metrics")
async def list_analysis() -> list[str]:
    async with conn.get_db_session() as db_session:
        dates = await metrics.list_metrics_dates(db_session)
    return [date.strftime("%Y-%m-%d") for date in dates]


@app.get("/metrics/{date}/")
async def get_analysis(date: str, rule: Optional[str] = None, index: StockIndex = StockIndex.SP500) -> dict:

    metrics_date = datetime.strptime(date, "%Y-%m-%d")
    # Get the symbols of the constituent
    symbols = await constituent.get_constituent_at(index, metrics_date.date())

    # Analyze the stock prices and save to database
    async with conn.get_db_session() as db_session:
        stock_metrics_batch = await metrics.get_stock_metrics_batch(
            db_session, symbols=symbols, metrics_date=metrics_date, back_period_weeks=52)

    # Apply rule if provided
    if rule:
        try:
            rule_func = compile_rule(rule)
            # Filter analyses using the rule (no max_stocks limit for API)
            stock_metrics_batch = [stock_metric for stock_metric in stock_metrics_batch if rule_func(stock_metric)]
            # Sort by rising stability score
            stock_metrics_batch = metrics_calculator.rank_by_rising_stability_score(stock_metrics_batch)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    return {
        "date": metrics_date.strftime("%Y-%m-%d"),
        "data": [stock_metric.model_dump() for stock_metric in stock_metrics_batch],
    }


@app.post("/simulate")
async def simulate(simulation_config: SimulationConfig) -> EnqueuedJob:
    """
    Enqueue a simulation job and return the job ID for status polling.
    """
    # Populate involved_keys from rule if not provided
    if not simulation_config.involved_keys:
        simulation_config.involved_keys = extract_involved_keys(simulation_config.rule)

    # Validate rule before enqueuing
    try:
        compile_rule(simulation_config.rule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    async with conn.get_db_session() as db_session:
        job_id = await queries.create_simulation_job(db_session, simulation_config)

    return EnqueuedJob(job_id=job_id, status="pending")


@app.get("/jobs/{job_id}")
async def get_job(job_id: UUID) -> SimulationJob:
    """Return the status of a simulation job."""
    async with conn.get_db_session() as db_session:
        job = await queries.get_job_by_id(db_session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@app.get("/jobs")
async def list_jobs() -> list[SimulationJob]:
    """Return the most recent simulation jobs."""
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
            prices = await market_data.get_index_prices(db_session, StockIndex.SP500, datetime.now() - timedelta(weeks=700), datetime.now())
            return [price.model_dump() for price in prices]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch S&P 500 data: {str(e)}"
            )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
