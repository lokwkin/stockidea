"""API routes for backtest operations."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from stockidea.backtest.backtester import Backtester
from stockidea.datasource.database import conn, queries
from stockidea.rule_engine import compile_ranking, compile_rule, extract_involved_keys
from stockidea.types import BacktestConfig, BacktestJob, EnqueuedJob, StockIndex

logger = logging.getLogger(__name__)

router = APIRouter()


async def worker_loop() -> None:
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
                        ranking_func=compile_ranking(config.ranking),
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


@router.get("/backtests")
async def list_backtests() -> list[dict]:
    """Return list of available backtests from database."""
    async with conn.get_db_session() as db_session:
        backtests = await queries.list_backtests(db_session)
        return backtests


@router.get("/backtests/{backtest_id}")
async def get_backtest(backtest_id: UUID) -> dict:
    """Return the full JSON content of a backtest by ID."""
    async with conn.get_db_session() as db_session:
        backtest_result = await queries.get_backtest_by_id(db_session, backtest_id)
        if backtest_result is None:
            raise HTTPException(
                status_code=404, detail=f"Backtest not found: {backtest_id}"
            )
        return backtest_result.model_dump()


@router.post("/backtest")
async def create_backtest(backtest_config: BacktestConfig) -> EnqueuedJob:
    """Enqueue a backtest job and return the job ID for status polling."""
    if not backtest_config.involved_keys:
        backtest_config.involved_keys = extract_involved_keys(backtest_config.rule)

    try:
        compile_rule(backtest_config.rule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    async with conn.get_db_session() as db_session:
        job_id = await queries.create_backtest_job(db_session, backtest_config)

    return EnqueuedJob(job_id=job_id, status="pending")


@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID) -> BacktestJob:
    """Return the status of a backtest job."""
    async with conn.get_db_session() as db_session:
        job = await queries.get_job_by_id(db_session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.get("/jobs")
async def list_jobs() -> list[BacktestJob]:
    """Return the most recent backtest jobs."""
    async with conn.get_db_session() as db_session:
        return await queries.list_recent_jobs(db_session)
