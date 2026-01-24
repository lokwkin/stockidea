"""PostgreSQL database implementation for storing price data using SQLAlchemy."""

from datetime import date, datetime, timedelta
import logging
from uuid import UUID

from sqlalchemy import (
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from stockidea.datasource.database.models import (
    DBStockPrice,
    DBStockPriceMetadata,
    DBSimulation,
    DBRebalanceHistory,
    DBInvestment,
)
from stockidea.types import (
    FMPAdjustedStockPrice,
    FMPLightPrice,
    StockIndex,
    StockPrice,
    SimulationResult,
    Investment,
    RebalanceHistory,
    SimulationConfig,
)

logger = logging.getLogger(__name__)


async def save_index_prices(db_session: AsyncSession, index: StockIndex, prices: list[FMPLightPrice]) -> None:
    logger.info(f"Saving index prices for {index.value}")
    # Delete existing entries for this index
    delete_prices_stmt = delete(DBStockPrice).where(DBStockPrice.symbol == index.value)
    delete_metadata_stmt = delete(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == index.value)
    await db_session.execute(delete_prices_stmt)
    await db_session.execute(delete_metadata_stmt)
    await db_session.commit()

    # Insert new entries
    for price in prices:
        price_record = DBStockPrice(
            symbol=index.value, date=date.fromisoformat(price.date), adj_close=price.price, close=price.price, volume=price.volume)
        db_session.add(price_record)

    # Update metadata for this index
    metadata = DBStockPriceMetadata(symbol=index.value, fetched_at=datetime.now())
    db_session.add(metadata)
    await db_session.commit()


async def save_stock_prices(db_session: AsyncSession, symbol: str, prices: list[FMPAdjustedStockPrice]) -> None:

    # Delete existing entries for this symbol
    delete_prices_stmt = delete(DBStockPrice).where(DBStockPrice.symbol == symbol.upper())
    delete_metadata_stmt = delete(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == symbol.upper())
    await db_session.execute(delete_prices_stmt)
    await db_session.execute(delete_metadata_stmt)
    await db_session.commit()

    # Insert new entries
    for price_data in prices:
        price_record = DBStockPrice(
            symbol=symbol.upper(),
            date=date.fromisoformat(price_data.date),
            open=price_data.adjOpen,
            high=price_data.adjHigh,
            low=price_data.adjLow,
            close=price_data.adjClose,
            adj_close=price_data.adjClose,
            volume=price_data.volume,
            created_at=datetime.now(),
        )
        db_session.add(price_record)

    # Update metadata for this symbol
    metadata = DBStockPriceMetadata(
        symbol=symbol.upper(),
        fetched_at=datetime.now(),
    )
    db_session.add(metadata)

    await db_session.commit()


async def is_data_fresh(db_session: AsyncSession, symbol: str) -> bool:
    stmt = select(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == symbol.upper())
    result = await db_session.execute(stmt)
    metadata = result.scalar_one_or_none()
    # if the symbol prices are last fetched more than 1 day ago, return False
    if metadata is None:
        return False

    return metadata.fetched_at > datetime.now() - timedelta(days=1)


async def get_prices_by_date_range(db_session: AsyncSession, symbol: str, from_date: date, to_date: date) -> list[StockPrice]:
    """
    Get the stock prices for a given symbol and date range.
    """
    stmt = select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close).where(DBStockPrice.symbol == symbol.upper()).where(
        DBStockPrice.date >= from_date).where(DBStockPrice.date <= to_date).order_by(DBStockPrice.date.desc())
    result = await db_session.execute(stmt)
    prices = result.all()  # Returns Row objects when selecting multiple columns
    return [StockPrice(
        symbol=price.symbol,
        date=price.date,
        adj_close=price.adj_close
    ) for price in prices]


async def get_price_by_date(db_session: AsyncSession, symbol: str, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Get the stock price for a given symbol and date.
    If nearest is True, and the price is not found for the given date, return the price for the nearest date before the given date.
    """
    stmt = select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close).where(DBStockPrice.symbol == symbol.upper()).where(
        DBStockPrice.date == target_date).order_by(DBStockPrice.date.desc())
    result = await db_session.execute(stmt)
    price = result.first()  # Returns Row object or None when selecting multiple columns
    if price is not None:
        return StockPrice(
            symbol=price.symbol,
            date=price.date,
            adj_close=price.adj_close
        )
    if nearest:
        # Find the price of nearest date we have before the target date
        stmt = select(DBStockPrice.symbol, DBStockPrice.date, DBStockPrice.adj_close).where(DBStockPrice.symbol == symbol.upper()).where(
            DBStockPrice.date < target_date).order_by(DBStockPrice.date.desc()).limit(1)
        result = await db_session.execute(stmt)
        price = result.first()  # Returns Row object or None when selecting multiple columns
        if price is not None:
            return StockPrice(
                symbol=price.symbol,
                date=price.date,
                adj_close=price.adj_close
            )

    raise ValueError(f"No price data available for symbol: {symbol} on date: {target_date}")


async def save_simulation_result(db_session: AsyncSession, result: SimulationResult) -> UUID:
    """
    Save a simulation result to the database.
    Returns the simulation ID.
    """
    logger.info("Saving simulation result to database")

    # Create simulation record
    simulation = DBSimulation(
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
        max_stocks=result.simulation_config.max_stocks,
        rebalance_interval_weeks=result.simulation_config.rebalance_interval_weeks,
        rule=result.simulation_config.rule,
        index=result.simulation_config.index.value,
    )
    db_session.add(simulation)
    await db_session.flush()  # Flush to get the simulation ID
    simulation_id = simulation.id  # Store ID before commit to avoid greenlet issues

    # Create rebalance history records
    for rebalance in result.rebalance_history:
        rebalance_history = DBRebalanceHistory(
            simulation_id=simulation_id,
            date=rebalance.date,
            balance=rebalance.balance,
            analysis_ref=rebalance.analysis_ref,
            profit_pct=rebalance.profit_pct,
            profit=rebalance.profit,
            baseline_profit_pct=rebalance.baseline_profit_pct,
            baseline_profit=rebalance.baseline_profit,
            baseline_balance=rebalance.baseline_balance,
        )
        db_session.add(rebalance_history)
        await db_session.flush()  # Flush to get the rebalance_history ID

        # Create investment records
        for investment in rebalance.investments:
            investment_record = DBInvestment(
                rebalance_history_id=rebalance_history.id,
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
    logger.info(f"✓ Simulation result saved to database with ID: {simulation_id}")
    return simulation_id


async def get_simulation_by_id(db_session: AsyncSession, simulation_id: UUID) -> SimulationResult | None:
    """
    Get a simulation result by ID from the database.
    """
    stmt = (
        select(DBSimulation)
        .where(DBSimulation.id == simulation_id)
        .options(
            selectinload(DBSimulation.rebalance_histories).selectinload(DBRebalanceHistory.investments)
        )
    )
    result = await db_session.execute(stmt)
    simulation = result.scalar_one_or_none()

    if simulation is None:
        return None

    return _db_simulation_to_result(simulation)


async def list_simulations(db_session: AsyncSession, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    List simulations from the database.
    Returns a list of simulation summaries (id, date_start, date_end, profit_pct, created_at).
    """
    stmt = (
        select(DBSimulation)
        .order_by(DBSimulation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db_session.execute(stmt)
    simulations = result.scalars().all()

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
        for sim in simulations
    ]


def _db_simulation_to_result(db_simulation: DBSimulation) -> SimulationResult:
    """Convert a DBSimulation database object to a SimulationResult Pydantic model."""
    rebalance_histories = []
    for db_rebalance in db_simulation.rebalance_histories:
        investments = [
            Investment(
                symbol=inv.symbol,
                position=inv.position,
                buy_price=inv.buy_price,
                buy_date=inv.buy_date,
                sell_price=inv.sell_price,
                sell_date=inv.sell_date,
                profit_pct=inv.profit_pct,
                profit=inv.profit,
            )
            for inv in db_rebalance.investments
        ]
        rebalance_histories.append(
            RebalanceHistory(
                date=db_rebalance.date,
                balance=db_rebalance.balance,
                analysis_ref=db_rebalance.analysis_ref,
                investments=investments,
                profit_pct=db_rebalance.profit_pct,
                profit=db_rebalance.profit,
                baseline_profit_pct=db_rebalance.baseline_profit_pct,
                baseline_profit=db_rebalance.baseline_profit,
                baseline_balance=db_rebalance.baseline_balance,
            )
        )

    return SimulationResult(
        initial_balance=db_simulation.initial_balance,
        final_balance=db_simulation.final_balance,
        date_start=db_simulation.date_start,
        date_end=db_simulation.date_end,
        rebalance_history=rebalance_histories,
        profit_pct=db_simulation.profit_pct,
        profit=db_simulation.profit,
        baseline_index=StockIndex(db_simulation.baseline_index),
        baseline_profit_pct=db_simulation.baseline_profit_pct,
        baseline_profit=db_simulation.baseline_profit,
        baseline_balance=db_simulation.baseline_balance,
        simulation_config=SimulationConfig(
            max_stocks=db_simulation.max_stocks,
            rebalance_interval_weeks=db_simulation.rebalance_interval_weeks,
            date_start=db_simulation.date_start,
            date_end=db_simulation.date_end,
            rule=db_simulation.rule,
            index=StockIndex(db_simulation.index),
        ),
    )
