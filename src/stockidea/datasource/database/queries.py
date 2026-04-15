"""PostgreSQL database implementation for storing price data using SQLAlchemy."""

from datetime import date, datetime, timedelta
import logging
from uuid import UUID

from sqlalchemy import (
    delete,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from stockidea.datasource.database.models import (
    DBStockPrice,
    DBStockPriceMetadata,
    DBConstituentChange,
    DBConstituentMetadata,
    DBBacktest,
    DBBacktestRebalance,
    DBBacktestInvestment,
    DBStockIndicators,
    DBBacktestJob,
)
from stockidea.rule_engine import extract_involved_keys
from stockidea.types import (
    ConstituentChange,
    FMPAdjustedStockPrice,
    FMPLightPrice,
    StockIndex,
    StockPrice,
    BacktestResult,
    BacktestInvestment,
    BacktestRebalance,
    BacktestConfig,
    StockIndicators,
    BacktestJob,
)

logger = logging.getLogger(__name__)


async def save_index_prices(
    db_session: AsyncSession, index: StockIndex, prices: list[FMPLightPrice]
) -> None:
    now = datetime.now()
    logger.info(f"Saving {len(prices)} index prices for {index.value}")

    for p in prices:
        stmt = pg_insert(DBStockPrice).values(
            symbol=index.value,
            date=date.fromisoformat(p.date),
            adj_close=p.price,
            close=p.price,
            volume=p.volume,
            created_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
                "created_at": stmt.excluded.created_at,
            },
        )
        await db_session.execute(stmt)

    # Upsert metadata
    meta_stmt = pg_insert(DBStockPriceMetadata).values(
        symbol=index.value, fetched_at=now
    )
    meta_stmt = meta_stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_={"fetched_at": meta_stmt.excluded.fetched_at},
    )
    await db_session.execute(meta_stmt)

    await db_session.commit()


async def save_stock_prices(
    db_session: AsyncSession, symbol: str, prices: list[FMPAdjustedStockPrice]
) -> None:
    upper_symbol = symbol.upper()
    now = datetime.now()
    logger.info(f"Saving {len(prices)} prices for {upper_symbol}")

    for p in prices:
        stmt = pg_insert(DBStockPrice).values(
            symbol=upper_symbol,
            date=date.fromisoformat(p.date),
            open=p.adjOpen,
            high=p.adjHigh,
            low=p.adjLow,
            close=p.adjClose,
            adj_close=p.adjClose,
            volume=p.volume,
            created_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
                "created_at": stmt.excluded.created_at,
            },
        )
        await db_session.execute(stmt)

    # Upsert metadata
    meta_stmt = pg_insert(DBStockPriceMetadata).values(
        symbol=upper_symbol, fetched_at=now
    )
    meta_stmt = meta_stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_={"fetched_at": meta_stmt.excluded.fetched_at},
    )
    await db_session.execute(meta_stmt)

    await db_session.commit()


async def get_last_fetched_at(
    db_session: AsyncSession, symbol: str
) -> datetime | None:
    """Get the last fetched_at timestamp for a symbol, or None if never fetched."""
    stmt = select(DBStockPriceMetadata.fetched_at).where(
        DBStockPriceMetadata.symbol == symbol.upper()
    )
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def is_data_fresh(db_session: AsyncSession, symbol: str) -> bool:
    fetched_at = await get_last_fetched_at(db_session, symbol)
    if fetched_at is None:
        return False
    return fetched_at > datetime.now() - timedelta(days=1)


# =============================================================================
# Constituent Change Queries
# =============================================================================


async def save_constituent_changes(
    db_session: AsyncSession,
    index: StockIndex,
    changes: list[ConstituentChange],
) -> None:
    """Replace all constituent changes for an index and update metadata."""
    # Delete existing
    await db_session.execute(
        delete(DBConstituentChange).where(DBConstituentChange.index == index.value)
    )
    await db_session.execute(
        delete(DBConstituentMetadata).where(DBConstituentMetadata.index == index.value)
    )
    await db_session.flush()

    # Insert new
    for change in changes:
        db_session.add(
            DBConstituentChange(
                index=index.value,
                date=change.date,
                added_symbol=change.added_symbol,
                removed_symbol=change.removed_symbol,
            )
        )

    db_session.add(DBConstituentMetadata(index=index.value, fetched_at=datetime.now()))
    await db_session.commit()


async def load_constituent_changes(
    db_session: AsyncSession,
    index: StockIndex,
) -> list[ConstituentChange] | None:
    """Load constituent changes for an index. Returns None if stale or missing."""
    # Check freshness
    meta_stmt = select(DBConstituentMetadata).where(
        DBConstituentMetadata.index == index.value
    )
    meta_result = await db_session.execute(meta_stmt)
    metadata = meta_result.scalar_one_or_none()
    if metadata is None or metadata.fetched_at < datetime.now() - timedelta(days=1):
        return None

    # Load changes
    changes_stmt = (
        select(DBConstituentChange)
        .where(DBConstituentChange.index == index.value)
        .order_by(DBConstituentChange.date)
    )
    changes_result = await db_session.execute(changes_stmt)
    rows = changes_result.scalars().all()

    return [
        ConstituentChange(
            date=row.date,
            added_symbol=row.added_symbol,
            removed_symbol=row.removed_symbol,
        )
        for row in rows
    ]


async def is_constituent_data_fresh(
    db_session: AsyncSession, index: StockIndex
) -> bool:
    """Check if constituent data for an index was fetched today."""
    stmt = select(DBConstituentMetadata).where(
        DBConstituentMetadata.index == index.value
    )
    result = await db_session.execute(stmt)
    metadata = result.scalar_one_or_none()
    if metadata is None:
        return False
    return metadata.fetched_at > datetime.now() - timedelta(days=1)


async def get_prices_by_date_range(
    db_session: AsyncSession, symbol: str, from_date: date, to_date: date
) -> list[StockPrice]:
    """
    Get the stock prices for a given symbol and date range.
    """
    stmt = (
        select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close)
        .where(DBStockPrice.symbol == symbol.upper())
        .where(DBStockPrice.date >= from_date)
        .where(DBStockPrice.date <= to_date)
        .order_by(DBStockPrice.date.desc())
    )
    result = await db_session.execute(stmt)
    prices = result.all()  # Returns Row objects when selecting multiple columns
    return [
        StockPrice(symbol=price.symbol, date=price.date, adj_close=price.adj_close)
        for price in prices
    ]


async def get_price_by_date(
    db_session: AsyncSession, symbol: str, target_date: date, nearest: bool = False
) -> StockPrice:
    """
    Get the stock price for a given symbol and date.
    If nearest is True, and the price is not found for the given date, return the price for the nearest date before the given date.
    """
    stmt = (
        select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close)
        .where(DBStockPrice.symbol == symbol.upper())
        .where(DBStockPrice.date == target_date)
        .order_by(DBStockPrice.date.desc())
    )
    result = await db_session.execute(stmt)
    price = result.first()  # Returns Row object or None when selecting multiple columns
    if price is not None:
        return StockPrice(
            symbol=price.symbol, date=price.date, adj_close=price.adj_close
        )
    if nearest:
        # Find the price of nearest date we have before the target date
        stmt = (
            select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close)
            .where(DBStockPrice.symbol == symbol.upper())
            .where(DBStockPrice.date < target_date)
            .order_by(DBStockPrice.date.desc())
            .limit(1)
        )
        result = await db_session.execute(stmt)
        price = (
            result.first()
        )  # Returns Row object or None when selecting multiple columns
        if price is not None:
            return StockPrice(
                symbol=price.symbol, date=price.date, adj_close=price.adj_close
            )

    raise ValueError(
        f"No price data available for symbol: {symbol} on date: {target_date}"
    )


async def save_backtest_result(
    db_session: AsyncSession, result: BacktestResult
) -> UUID:
    """
    Save a backtest result to the database.
    Returns the backtest ID.
    """
    logger.info("Saving backtest result to database")

    # Create backtest record
    backtest = DBBacktest(
        initial_balance=result.initial_balance,
        final_balance=result.final_balance,
        date_start=result.date_start,
        date_end=result.date_end,
        profit_pct=result.profit_pct,
        profit=result.profit,
        baseline_index=result.baseline_index.value,
        baseline_profit_pct=result.baseline_profit_pct,
        baseline_profit=result.baseline_profit,
        baseline_balance=result.baseline_balance,
        max_stocks=result.backtest_config.max_stocks,
        rebalance_interval_weeks=result.backtest_config.rebalance_interval_weeks,
        rule=result.backtest_config.rule,
        index=result.backtest_config.index.value,
    )
    db_session.add(backtest)
    await db_session.flush()  # Flush to get the backtest ID
    backtest_id = backtest.id  # Store ID before commit to avoid greenlet issues

    # Create rebalance history records
    for rebalance in result.backtest_rebalance:
        backtest_rebalance = DBBacktestRebalance(
            backtest_id=backtest_id,
            date=rebalance.date,
            balance=rebalance.balance,
            profit_pct=rebalance.profit_pct,
            profit=rebalance.profit,
            baseline_profit_pct=rebalance.baseline_profit_pct,
            baseline_profit=rebalance.baseline_profit,
            baseline_balance=rebalance.baseline_balance,
        )
        db_session.add(backtest_rebalance)
        await db_session.flush()  # Flush to get the backtest_rebalance ID

        # Create investment records
        for investment in rebalance.investments:
            investment_record = DBBacktestInvestment(
                backtest_rebalance_id=backtest_rebalance.id,
                symbol=investment.symbol,
                position=investment.position,
                buy_price=investment.buy_price,
                buy_date=investment.buy_date,
                sell_price=investment.sell_price,
                sell_date=investment.sell_date,
                profit_pct=investment.profit_pct,
                profit=investment.profit,
            )
            db_session.add(investment_record)

    await db_session.commit()
    logger.info(f"✓ Backtest result saved to database with ID: {backtest_id}")
    return backtest_id


async def get_backtest_by_id(
    db_session: AsyncSession, backtest_id: UUID
) -> BacktestResult | None:
    """
    Get a backtest result by ID from the database.
    """
    stmt = (
        select(DBBacktest)
        .where(DBBacktest.id == backtest_id)
        .options(
            selectinload(DBBacktest.backtest_rebalances).selectinload(
                DBBacktestRebalance.backtest_investments
            )
        )
    )
    result = await db_session.execute(stmt)
    backtest = result.scalar_one_or_none()

    if backtest is None:
        return None

    return _db_backtest_to_result(backtest)


async def list_backtests(
    db_session: AsyncSession, limit: int = 100, offset: int = 0
) -> list[dict]:
    """
    List backtests from the database.
    Returns a list of backtest summaries (id, date_start, date_end, profit_pct, created_at).
    """
    stmt = (
        select(DBBacktest)
        .order_by(DBBacktest.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db_session.execute(stmt)
    backtests = result.scalars().all()

    return [
        {
            "id": sim.id,
            "date_start": sim.date_start.isoformat(),
            "date_end": sim.date_end.isoformat(),
            "profit_pct": sim.profit_pct,
            "profit": sim.profit,
            "baseline_profit_pct": sim.baseline_profit_pct,
            "created_at": sim.created_at.isoformat(),
        }
        for sim in backtests
    ]


def _db_backtest_to_result(db_backtest: DBBacktest) -> BacktestResult:
    """Convert a DBBacktest database object to a BacktestResult Pydantic model."""
    backtest_rebalances = []
    for db_rebalance in db_backtest.backtest_rebalances:
        investments = [
            BacktestInvestment(
                symbol=inv.symbol,
                position=inv.position,
                buy_price=inv.buy_price,
                buy_date=inv.buy_date,
                sell_price=inv.sell_price,
                sell_date=inv.sell_date,
                profit_pct=inv.profit_pct,
                profit=inv.profit,
            )
            for inv in db_rebalance.backtest_investments
        ]
        backtest_rebalances.append(
            BacktestRebalance(
                date=db_rebalance.date,
                balance=db_rebalance.balance,
                investments=investments,
                profit_pct=db_rebalance.profit_pct,
                profit=db_rebalance.profit,
                baseline_profit_pct=db_rebalance.baseline_profit_pct,
                baseline_profit=db_rebalance.baseline_profit,
                baseline_balance=db_rebalance.baseline_balance,
            )
        )

    return BacktestResult(
        initial_balance=db_backtest.initial_balance,
        final_balance=db_backtest.final_balance,
        date_start=db_backtest.date_start,
        date_end=db_backtest.date_end,
        backtest_rebalance=backtest_rebalances,
        profit_pct=db_backtest.profit_pct,
        profit=db_backtest.profit,
        baseline_index=StockIndex(db_backtest.baseline_index),
        baseline_profit_pct=db_backtest.baseline_profit_pct,
        baseline_profit=db_backtest.baseline_profit,
        baseline_balance=db_backtest.baseline_balance,
        backtest_config=BacktestConfig(
            max_stocks=db_backtest.max_stocks,
            rebalance_interval_weeks=db_backtest.rebalance_interval_weeks,
            date_start=db_backtest.date_start,
            date_end=db_backtest.date_end,
            rule=db_backtest.rule,
            index=StockIndex(db_backtest.index),
            involved_keys=extract_involved_keys(db_backtest.rule),
        ),
    )


# =============================================================================
# Stock Indicator Queries
# =============================================================================


async def save_stock_indicators(
    db_session: AsyncSession,
    stock_indicators: StockIndicators,
    indicators_date: date,
) -> None:
    """Save stock indicators to the database for a specific date."""
    logger.info(f"Saving indicators for {stock_indicators.symbol} on {indicators_date}")

    record = DBStockIndicators(**stock_indicators.model_dump())
    await db_session.merge(record)

    await db_session.commit()


async def load_stock_indicators(
    db_session: AsyncSession,
    symbol: str,
    indicators_date: date,
) -> StockIndicators | None:
    """Load stock indicators for a specific date from the database.

    Returns a StockIndicators object, or None if no data found.
    """
    stmt = (
        select(DBStockIndicators)
        .where(DBStockIndicators.symbol == symbol.upper())
        .where(DBStockIndicators.date == indicators_date)
    )
    result = await db_session.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        return None

    return StockIndicators(
        symbol=record.symbol,
        date=record.date,
        total_weeks=record.total_weeks,
        linear_slope_pct=record.linear_slope_pct,
        linear_r_squared=record.linear_r_squared,
        log_slope=record.log_slope,
        log_r_squared=record.log_r_squared,
        change_1w_pct=record.change_1w_pct,
        change_2w_pct=record.change_2w_pct,
        change_4w_pct=record.change_4w_pct,
        change_13w_pct=record.change_13w_pct,
        change_26w_pct=record.change_26w_pct,
        change_1y_pct=record.change_1y_pct,
        max_jump_1w_pct=record.max_jump_1w_pct,
        max_drop_1w_pct=record.max_drop_1w_pct,
        max_jump_2w_pct=record.max_jump_2w_pct,
        max_drop_2w_pct=record.max_drop_2w_pct,
        max_jump_4w_pct=record.max_jump_4w_pct,
        max_drop_4w_pct=record.max_drop_4w_pct,
        weekly_return_std=record.weekly_return_std,
        downside_std=record.downside_std,
        max_drawdown_pct=record.max_drawdown_pct,
        pct_weeks_positive=record.pct_weeks_positive,
        slope_13w_pct=record.slope_13w_pct,
        r_squared_13w=record.r_squared_13w,
        r_squared_4w=record.r_squared_4w,
        slope_26w_pct=record.slope_26w_pct,
        r_squared_26w=record.r_squared_26w,
        acceleration_13w=record.acceleration_13w,
        pct_from_4w_high=record.pct_from_4w_high,
    )


async def list_indicator_dates(db_session: AsyncSession) -> list[datetime]:
    stmt = (
        select(DBStockIndicators.date)
        .distinct()
        .order_by(DBStockIndicators.date.desc())
    )
    result = await db_session.execute(stmt)
    return [datetime.fromisoformat(date.isoformat()) for date in result.scalars().all()]


# =============================================================================
# Backtest Job Queue Queries
# =============================================================================


async def create_backtest_job(
    db_session: AsyncSession, config: BacktestConfig
) -> UUID:
    """Enqueue a new backtest job. Returns the job ID."""
    job = DBBacktestJob(
        status="pending",
        config_json=config.model_dump_json(),
    )
    db_session.add(job)
    await db_session.flush()
    job_id = job.id
    await db_session.commit()
    logger.info(f"Backtest job enqueued: {job_id}")
    return job_id


async def get_job_by_id(db_session: AsyncSession, job_id: UUID) -> BacktestJob | None:
    """Return BacktestJob or None if not found."""
    stmt = select(DBBacktestJob).where(DBBacktestJob.id == job_id)
    result = await db_session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        return None
    return _job_to_model(job)


async def list_recent_jobs(
    db_session: AsyncSession, limit: int = 50
) -> list[BacktestJob]:
    """List recent backtest jobs ordered by creation time descending."""
    stmt = (
        select(DBBacktestJob).order_by(DBBacktestJob.created_at.desc()).limit(limit)
    )
    result = await db_session.execute(stmt)
    return [_job_to_model(job) for job in result.scalars().all()]


async def claim_next_pending_job(db_session: AsyncSession) -> DBBacktestJob | None:
    """
    Atomically claim the oldest pending job by setting its status to 'running'.
    Uses SKIP LOCKED so concurrent workers don't double-claim.
    Returns the claimed job row, or None if no pending jobs exist.
    """
    stmt = (
        select(DBBacktestJob)
        .where(DBBacktestJob.status == "pending")
        .order_by(DBBacktestJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = await db_session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        return None

    job.status = "running"
    job.started_at = datetime.now()
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def mark_job_completed(
    db_session: AsyncSession, job_id: UUID, backtest_id: UUID
) -> None:
    stmt = (
        update(DBBacktestJob)
        .where(DBBacktestJob.id == job_id)
        .values(
            status="completed", backtest_id=backtest_id, completed_at=datetime.now()
        )
    )
    await db_session.execute(stmt)
    await db_session.commit()


async def mark_job_failed(
    db_session: AsyncSession, job_id: UUID, error_message: str
) -> None:
    stmt = (
        update(DBBacktestJob)
        .where(DBBacktestJob.id == job_id)
        .values(
            status="failed", error_message=error_message, completed_at=datetime.now()
        )
    )
    await db_session.execute(stmt)
    await db_session.commit()


def _job_to_model(job: DBBacktestJob) -> BacktestJob:
    return BacktestJob(
        id=job.id,
        status=job.status,
        backtest_id=job.backtest_id,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
