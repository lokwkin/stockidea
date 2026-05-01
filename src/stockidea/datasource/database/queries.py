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
    DBStockSma,
    DBStockSmaMetadata,
    DBMarketRegime,
    DBConstituentChange,
    DBConstituentMetadata,
    DBBacktest,
    DBBacktestRebalance,
    DBBacktestInvestment,
    DBStockIndicators,
    DBStrategy,
    DBStrategyMessage,
)
from stockidea.rule_engine import extract_involved_keys
from stockidea.types import (
    ConstituentChange,
    FMPAdjustedStockPrice,
    FMPLightPrice,
    MarketRegime,
    StockIndex,
    StockPrice,
    BacktestResult,
    BacktestInvestment,
    BacktestRebalance,
    BacktestConfig,
    BacktestScores,
    StopLossConfig,
    StockIndicators,
    StrategyCreate,
    StrategySummary,
    StrategyDetail,
    StrategyMessage,
    StrategyBacktestSummary,
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


async def get_last_fetched_at(db_session: AsyncSession, symbol: str) -> datetime | None:
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
# Stock SMA Queries
# =============================================================================


async def save_stock_sma(
    db_session: AsyncSession,
    symbol: str,
    period_length: int,
    rows: list[tuple[date, float]],
) -> None:
    """Upsert daily SMA values for a (symbol, period_length)."""
    upper_symbol = symbol.upper()
    now = datetime.now()
    if rows:
        logger.info(f"Saving {len(rows)} SMA({period_length}) rows for {upper_symbol}")

    for sma_date, sma_value in rows:
        stmt = pg_insert(DBStockSma).values(
            symbol=upper_symbol,
            period_length=period_length,
            date=sma_date,
            sma_value=sma_value,
            created_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "period_length", "date"],
            set_={
                "sma_value": stmt.excluded.sma_value,
                "created_at": stmt.excluded.created_at,
            },
        )
        await db_session.execute(stmt)

    meta_stmt = pg_insert(DBStockSmaMetadata).values(
        symbol=upper_symbol, period_length=period_length, fetched_at=now
    )
    meta_stmt = meta_stmt.on_conflict_do_update(
        index_elements=["symbol", "period_length"],
        set_={"fetched_at": meta_stmt.excluded.fetched_at},
    )
    await db_session.execute(meta_stmt)
    await db_session.commit()


async def get_sma_fetched_at(
    db_session: AsyncSession, symbol: str, period_length: int
) -> datetime | None:
    stmt = select(DBStockSmaMetadata.fetched_at).where(
        DBStockSmaMetadata.symbol == symbol.upper(),
        DBStockSmaMetadata.period_length == period_length,
    )
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def is_sma_fresh(
    db_session: AsyncSession, symbol: str, period_length: int
) -> bool:
    fetched_at = await get_sma_fetched_at(db_session, symbol, period_length)
    if fetched_at is None:
        return False
    return fetched_at > datetime.now() - timedelta(days=1)


async def load_stock_sma(
    db_session: AsyncSession,
    symbol: str,
    period_length: int,
    from_date: date,
    to_date: date,
) -> list[tuple[date, float]]:
    """Load cached SMA values for a (symbol, period_length) over a date range, ascending."""
    stmt = (
        select(DBStockSma.date, DBStockSma.sma_value)
        .where(DBStockSma.symbol == symbol.upper())
        .where(DBStockSma.period_length == period_length)
        .where(DBStockSma.date >= from_date)
        .where(DBStockSma.date <= to_date)
        .order_by(DBStockSma.date.asc())
    )
    result = await db_session.execute(stmt)
    return [(row.date, row.sma_value) for row in result.all()]


async def get_sma_at_or_before(
    db_session: AsyncSession,
    symbol: str,
    period_length: int,
    target_date: date,
) -> float | None:
    """Return the most recent SMA value on/before target_date (or None if missing)."""
    stmt = (
        select(DBStockSma.sma_value)
        .where(DBStockSma.symbol == symbol.upper())
        .where(DBStockSma.period_length == period_length)
        .where(DBStockSma.date <= target_date)
        .order_by(DBStockSma.date.desc())
        .limit(1)
    )
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_sma_per_symbol(
    db_session: AsyncSession,
    symbols: list[str],
    period_length: int,
    target_date: date,
) -> dict[str, float]:
    """Batch: for each symbol, return latest SMA value on/before target_date."""
    if not symbols:
        return {}
    upper_symbols = [s.upper() for s in symbols]
    stmt = (
        select(DBStockSma.symbol, DBStockSma.sma_value)
        .distinct(DBStockSma.symbol)
        .where(DBStockSma.symbol.in_(upper_symbols))
        .where(DBStockSma.period_length == period_length)
        .where(DBStockSma.date <= target_date)
        .order_by(DBStockSma.symbol, DBStockSma.date.desc())
    )
    result = await db_session.execute(stmt)
    return {row.symbol: row.sma_value for row in result.all()}


async def get_latest_price_per_symbol(
    db_session: AsyncSession, symbols: list[str], target_date: date
) -> dict[str, float]:
    """Batch: for each symbol, return latest adj_close on/before target_date."""
    if not symbols:
        return {}
    upper_symbols = [s.upper() for s in symbols]
    stmt = (
        select(DBStockPrice.symbol, DBStockPrice.adj_close)
        .distinct(DBStockPrice.symbol)
        .where(DBStockPrice.symbol.in_(upper_symbols))
        .where(DBStockPrice.date <= target_date)
        .order_by(DBStockPrice.symbol, DBStockPrice.date.desc())
    )
    result = await db_session.execute(stmt)
    return {row.symbol: row.adj_close for row in result.all()}


# =============================================================================
# Market Regime Queries
# =============================================================================


async def save_market_regime(db_session: AsyncSession, regime: MarketRegime) -> None:
    """Upsert a market regime row for an (index, date)."""
    stmt = pg_insert(DBMarketRegime).values(
        index=regime.index.value,
        date=regime.date,
        index_above_ma50=regime.index_above_ma50,
        index_above_ma200=regime.index_above_ma200,
        index_drawdown_pct_52w=regime.index_drawdown_pct_52w,
        breadth_pct_above_ma50=regime.breadth_pct_above_ma50,
        breadth_pct_above_ma200=regime.breadth_pct_above_ma200,
        created_at=datetime.now(),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["index", "date"],
        set_={
            "index_above_ma50": stmt.excluded.index_above_ma50,
            "index_above_ma200": stmt.excluded.index_above_ma200,
            "index_drawdown_pct_52w": stmt.excluded.index_drawdown_pct_52w,
            "breadth_pct_above_ma50": stmt.excluded.breadth_pct_above_ma50,
            "breadth_pct_above_ma200": stmt.excluded.breadth_pct_above_ma200,
            "created_at": stmt.excluded.created_at,
        },
    )
    await db_session.execute(stmt)
    await db_session.commit()


async def load_market_regime(
    db_session: AsyncSession, index: StockIndex, target_date: date
) -> MarketRegime | None:
    stmt = (
        select(DBMarketRegime)
        .where(DBMarketRegime.index == index.value)
        .where(DBMarketRegime.date == target_date)
    )
    result = await db_session.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        return None
    return MarketRegime(
        index=StockIndex(record.index),
        date=record.date,
        index_above_ma50=record.index_above_ma50,
        index_above_ma200=record.index_above_ma200,
        index_drawdown_pct_52w=record.index_drawdown_pct_52w,
        breadth_pct_above_ma50=record.breadth_pct_above_ma50,
        breadth_pct_above_ma200=record.breadth_pct_above_ma200,
    )


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
        select(
            DBStockPrice.symbol,
            DBStockPrice.date,
            DBStockPrice.adj_close,
            DBStockPrice.low,
            DBStockPrice.volume,
        )
        .where(DBStockPrice.symbol == symbol.upper())
        .where(DBStockPrice.date >= from_date)
        .where(DBStockPrice.date <= to_date)
        .order_by(DBStockPrice.date.desc())
    )
    result = await db_session.execute(stmt)
    prices = result.all()
    return [
        StockPrice(
            symbol=price.symbol,
            date=price.date,
            adj_close=price.adj_close,
            low=price.low,
            volume=price.volume,
        )
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
    db_session: AsyncSession,
    result: BacktestResult,
    strategy_id: UUID | None = None,
) -> UUID:
    """
    Save a backtest result to the database.
    Returns the backtest ID.
    """
    logger.info("Saving backtest result to database")

    # Create backtest record
    backtest = DBBacktest(
        strategy_id=strategy_id,
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
        ranking=result.backtest_config.ranking,
        index=result.backtest_config.index.value,
        stop_loss_json=result.backtest_config.stop_loss.model_dump_json()
        if result.backtest_config.stop_loss
        else None,
        scores_json=result.scores.model_dump_json() if result.scores else None,
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
            "strategy_id": sim.strategy_id,
            "date_start": sim.date_start.isoformat(),
            "date_end": sim.date_end.isoformat(),
            "profit_pct": sim.profit_pct,
            "profit": sim.profit,
            "baseline_profit_pct": sim.baseline_profit_pct,
            "index": sim.index,
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
            ranking=db_backtest.ranking
            if db_backtest.ranking
            else BacktestConfig.model_fields["ranking"].default,
            index=StockIndex(db_backtest.index),
            involved_keys=extract_involved_keys(db_backtest.rule),
            stop_loss=StopLossConfig.model_validate_json(db_backtest.stop_loss_json)
            if db_backtest.stop_loss_json
            else None,
        ),
        scores=BacktestScores.model_validate_json(db_backtest.scores_json)
        if db_backtest.scores_json
        else None,
    )


# =============================================================================
# Stock Indicator Queries
# =============================================================================


async def save_stock_indicators(
    db_session: AsyncSession,
    stock_indicators: StockIndicators,
    indicators_date: date,
) -> None:
    """Save stock indicators to the database for a specific date.

    Market regime (`mkt_*`) fields are merged at read time and are NOT persisted on
    the per-stock row — strip them here.
    """
    logger.info(f"Saving indicators for {stock_indicators.symbol} on {indicators_date}")

    payload = {
        k: v
        for k, v in stock_indicators.model_dump().items()
        if not k.startswith("mkt_")
    }
    record = DBStockIndicators(**payload)
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
        slope_pct_13w=record.slope_pct_13w,
        slope_pct_26w=record.slope_pct_26w,
        slope_pct_52w=record.slope_pct_52w,
        r_squared_4w=record.r_squared_4w,
        r_squared_13w=record.r_squared_13w,
        r_squared_26w=record.r_squared_26w,
        r_squared_52w=record.r_squared_52w,
        log_slope_13w=record.log_slope_13w,
        log_r_squared_13w=record.log_r_squared_13w,
        log_slope_26w=record.log_slope_26w,
        log_r_squared_26w=record.log_r_squared_26w,
        log_slope_52w=record.log_slope_52w,
        log_r_squared_52w=record.log_r_squared_52w,
        change_pct_1w=record.change_pct_1w,
        change_pct_2w=record.change_pct_2w,
        change_pct_4w=record.change_pct_4w,
        change_pct_13w=record.change_pct_13w,
        change_pct_26w=record.change_pct_26w,
        change_pct_52w=record.change_pct_52w,
        max_jump_pct_1w=record.max_jump_pct_1w,
        max_drop_pct_1w=record.max_drop_pct_1w,
        max_jump_pct_2w=record.max_jump_pct_2w,
        max_drop_pct_2w=record.max_drop_pct_2w,
        max_jump_pct_4w=record.max_jump_pct_4w,
        max_drop_pct_4w=record.max_drop_pct_4w,
        return_std_52w=record.return_std_52w,
        downside_std_52w=record.downside_std_52w,
        max_drawdown_pct_4w=record.max_drawdown_pct_4w,
        max_drawdown_pct_13w=record.max_drawdown_pct_13w,
        max_drawdown_pct_26w=record.max_drawdown_pct_26w,
        max_drawdown_pct_52w=record.max_drawdown_pct_52w,
        pct_weeks_positive_4w=record.pct_weeks_positive_4w,
        pct_weeks_positive_13w=record.pct_weeks_positive_13w,
        pct_weeks_positive_26w=record.pct_weeks_positive_26w,
        pct_weeks_positive_52w=record.pct_weeks_positive_52w,
        acceleration_pct_13w=record.acceleration_pct_13w,
        from_high_pct_4w=record.from_high_pct_4w,
        price_vs_ma20_pct=record.price_vs_ma20_pct,
        price_vs_ma50_pct=record.price_vs_ma50_pct,
        price_vs_ma100_pct=record.price_vs_ma100_pct,
        price_vs_ma200_pct=record.price_vs_ma200_pct,
        ma50_vs_ma200_pct=record.ma50_vs_ma200_pct,
        rs_pct_4w=record.rs_pct_4w,
        rs_pct_13w=record.rs_pct_13w,
        rs_pct_26w=record.rs_pct_26w,
        rs_pct_52w=record.rs_pct_52w,
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
# Strategy Queries
# =============================================================================


async def create_strategy(
    db_session: AsyncSession,
    strategy_create: StrategyCreate,
    name: str,
    date_start: date,
    date_end: date,
) -> UUID:
    """Create a new strategy and return its ID."""
    strategy = DBStrategy(
        name=name,
        instruction=strategy_create.instruction,
        model=strategy_create.model,
        date_start=date_start,
        date_end=date_end,
        status="idle",
    )
    db_session.add(strategy)
    await db_session.flush()
    strategy_id = strategy.id
    await db_session.commit()
    logger.info(f"Strategy created: {strategy_id}")
    return strategy_id


async def get_strategy_by_id(
    db_session: AsyncSession, strategy_id: UUID
) -> StrategyDetail | None:
    """Get a strategy with its messages and linked backtests."""
    stmt = (
        select(DBStrategy)
        .where(DBStrategy.id == strategy_id)
        .options(
            selectinload(DBStrategy.messages),
            selectinload(DBStrategy.backtests),
        )
    )
    result = await db_session.execute(stmt)
    strategy = result.scalar_one_or_none()
    if strategy is None:
        return None

    messages = [
        StrategyMessage(
            id=msg.id,
            role=msg.role,
            content_json=msg.content_json,
            created_at=msg.created_at,
            sequence=msg.sequence,
        )
        for msg in strategy.messages
    ]

    backtests = [
        StrategyBacktestSummary(
            id=bt.id,
            rule=bt.rule,
            ranking=bt.ranking,
            profit_pct=bt.profit_pct,
            baseline_profit_pct=bt.baseline_profit_pct,
            max_stocks=bt.max_stocks,
            rebalance_interval_weeks=bt.rebalance_interval_weeks,
            index=bt.index,
            scores=BacktestScores.model_validate_json(bt.scores_json)
            if bt.scores_json
            else None,
            created_at=bt.created_at,
        )
        for bt in sorted(strategy.backtests, key=lambda b: b.created_at)
    ]

    return StrategyDetail(
        id=strategy.id,
        name=strategy.name,
        instruction=strategy.instruction,
        model=strategy.model,
        date_start=strategy.date_start,
        date_end=strategy.date_end,
        status=strategy.status,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
        messages=messages,
        backtests=backtests,
        llm_history_json=strategy.llm_history_json,
    )


async def list_strategies(
    db_session: AsyncSession, limit: int = 50
) -> list[StrategySummary]:
    """List strategies ordered by updated_at descending."""
    stmt = select(DBStrategy).order_by(DBStrategy.updated_at.desc()).limit(limit)
    result = await db_session.execute(stmt)
    strategies = result.scalars().all()
    return [
        StrategySummary(
            id=s.id,
            name=s.name,
            instruction=s.instruction,
            model=s.model,
            status=s.status,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in strategies
    ]


async def update_strategy_status(
    db_session: AsyncSession, strategy_id: UUID, status: str
) -> None:
    """Update the status of a strategy."""
    stmt = (
        update(DBStrategy)
        .where(DBStrategy.id == strategy_id)
        .values(status=status, updated_at=datetime.now())
    )
    await db_session.execute(stmt)
    await db_session.commit()


async def update_strategy_llm_history(
    db_session: AsyncSession, strategy_id: UUID, llm_history_json: str
) -> None:
    """Update the LLM conversation history for a strategy."""
    stmt = (
        update(DBStrategy)
        .where(DBStrategy.id == strategy_id)
        .values(llm_history_json=llm_history_json, updated_at=datetime.now())
    )
    await db_session.execute(stmt)
    await db_session.commit()


async def add_strategy_message(
    db_session: AsyncSession,
    strategy_id: UUID,
    role: str,
    content_json: str,
) -> UUID:
    """Add a message to a strategy conversation and return its ID."""
    # Get next sequence number
    stmt = (
        select(DBStrategyMessage.sequence)
        .where(DBStrategyMessage.strategy_id == strategy_id)
        .order_by(DBStrategyMessage.sequence.desc())
        .limit(1)
    )
    result = await db_session.execute(stmt)
    last_seq = result.scalar_one_or_none()
    next_seq = (last_seq or 0) + 1

    msg = DBStrategyMessage(
        strategy_id=strategy_id,
        role=role,
        content_json=content_json,
        sequence=next_seq,
    )
    db_session.add(msg)
    await db_session.flush()
    msg_id = msg.id
    await db_session.commit()
    return msg_id


async def delete_strategy(db_session: AsyncSession, strategy_id: UUID) -> bool:
    """Delete a strategy and all its messages. Returns True if found and deleted."""
    stmt = select(DBStrategy).where(DBStrategy.id == strategy_id)
    result = await db_session.execute(stmt)
    strategy = result.scalar_one_or_none()
    if strategy is None:
        return False
    await db_session.delete(strategy)
    await db_session.commit()
    return True


async def get_strategy_llm_history(
    db_session: AsyncSession, strategy_id: UUID
) -> tuple[str | None, str | None]:
    """Get the LLM history and model for a strategy. Returns (llm_history_json, model)."""
    stmt = select(DBStrategy.llm_history_json, DBStrategy.model).where(
        DBStrategy.id == strategy_id
    )
    result = await db_session.execute(stmt)
    row = result.first()
    if row is None:
        return None, None
    return row.llm_history_json, row.model
