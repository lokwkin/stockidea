"""CLI commands for stockidea using Click."""

import asyncio
import logging
import click
from datetime import datetime

# Import config to initialize logging
import stockidea.config  # noqa: F401
from stockidea.indicators import service as indicators_service
from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn
from stockidea.datasource.database.queries import (
    save_simulation_result as save_simulation_to_db,
)
from stockidea.rule_engine import compile_rule

from stockidea.simulation.simulator import Simulator
from stockidea.types import StockIndex, StockIndicators

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Stock analysis and simulation tool."""
    pass


async def _analyze(date: datetime, index: StockIndex) -> list[StockIndicators]:
    async with conn.get_db_session() as db_session:
        # Get the symbols of the constituent
        symbols = await datasource_service.get_constituent_at(
            db_session, index, date.date()
        )

        # Compute stock indicators and save to database
        stock_indicators_batch = await indicators_service.get_stock_indicators_batch(
            db_session,
            symbols=symbols,
            indicators_date=date,
            back_period_weeks=52,
            compute_if_not_exists=True,
        )

        return stock_indicators_batch


@cli.command("analyze", help="Analyze stock prices for a given date")
@click.option(
    "--date",
    "-d",
    type=str,
    required=False,
    default=datetime.now().strftime("%Y-%m-%d"),
    help="Analysis date in YYYY-MM-DD format",
)
@click.option(
    "--index",
    "-i",
    type=click.Choice([member.value for member in StockIndex]),
    required=False,
    default=StockIndex.SP500.value,
    help="Stock index to analyze",
)
def analyze(date: str, index: str):
    stock_index = StockIndex(index)
    try:
        date_parsed = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {date}. Use YYYY-MM-DD format.")

    asyncio.run(_analyze(date=date_parsed, index=stock_index))


@cli.command(
    "pick", help="Apply a rule onto analyzed stock prices for a given date range."
)
@click.option(
    "--date",
    "-d",
    type=str,
    required=False,
    default=datetime.now().strftime("%Y-%m-%d"),
    help="Analysis date in YYYY-MM-DD format",
)
@click.option(
    "--rule",
    "-r",
    type=str,
    required=True,
    help="Rule expression string (e.g., 'change_13w_pct > 10 AND max_drop_2w_pct > 15')",
)
@click.option(
    "--max-stocks",
    "-m",
    type=int,
    default=3,
    help="Maximum number of stocks to hold at once (default: 3)",
)
@click.option(
    "--index",
    "-i",
    type=click.Choice([member.value for member in StockIndex]),
    required=False,
    default=StockIndex.SP500.value,
    help="Stock index to analyze",
)
def pick(date: str, rule: str, max_stocks: int, index: str):
    stock_index = StockIndex(index)
    try:
        date_parsed = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {date}. Use YYYY-MM-DD format.")

    # Compile the rule
    try:
        rule_func = compile_rule(rule)
    except Exception as e:
        raise click.BadParameter(f"Invalid rule expression: {e}")

    stock_indicators_batch = asyncio.run(_analyze(date=date_parsed, index=stock_index))

    filtered_stocks = indicators_service.apply_rule(
        indicators_batch=stock_indicators_batch, rule_func=rule_func
    )

    selected_stocks = filtered_stocks[:max_stocks]
    logger.info(
        f"Selected: {[stock.symbol for stock in selected_stocks]} (from {len(filtered_stocks)} filtered)"
    )


@cli.command("simulate", help="Simulate investment strategy for a given date range.")
@click.option(
    "--max-stocks",
    type=int,
    default=3,
    help="Maximum number of stocks to hold at once (default: 3)",
)
@click.option(
    "--rebalance-interval-weeks",
    type=int,
    default=2,
    help="Rebalance interval in weeks (default: 2)",
)
@click.option(
    "--date-start",
    type=str,
    required=True,
    help="Simulation start date in YYYY-MM-DD format",
)
@click.option(
    "--date-end",
    type=str,
    required=True,
    help="Simulation end date in YYYY-MM-DD format",
)
@click.option(
    "--index",
    "-i",
    type=click.Choice([member.value for member in StockIndex]),
    required=False,
    default=StockIndex.SP500.value,
    help="Stock index to analyze",
)
@click.option(
    "--rule",
    "-r",
    type=str,
    help="Rule expression string (e.g., 'change_13w_pct > 10 AND max_drop_2w_pct > 15')",
)
def simulate(
    max_stocks: int,
    rebalance_interval_weeks: int,
    date_start: str,
    date_end: str,
    rule: str,
    index: str,
):
    stock_index = StockIndex(index)
    try:
        date_start_parsed = datetime.strptime(date_start, "%Y-%m-%d")
        date_end_parsed = datetime.strptime(date_end, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter("Invalid date format. Use YYYY-MM-DD format.")

    if date_start_parsed >= date_end_parsed:
        raise click.BadParameter("date_start must be before date_end")

    # Compile the rule
    try:
        rule_func = compile_rule(rule)
    except Exception as e:
        raise click.BadParameter(f"Invalid rule expression: {e}")

    click.echo(
        f"Running simulation from {date_start_parsed.date()} to {date_end_parsed.date()}"
    )
    click.echo(
        f"Max stocks: {max_stocks}, Rebalance interval: {rebalance_interval_weeks} weeks"
    )
    click.echo(f"Rule: {rule}")
    click.echo(f"Stock index: {stock_index}")

    async def _simulate_and_save():
        async with conn.get_db_session() as db_session:
            simulator = Simulator(
                db_session=db_session,
                max_stocks=max_stocks,
                rebalance_interval_weeks=rebalance_interval_weeks,
                date_start=date_start_parsed,
                date_end=date_end_parsed,
                rule_func=rule_func,
                rule_raw=rule,
                from_index=stock_index,
                baseline_index=StockIndex.SP500,
            )
            simulation_result = await simulator.simulate()
            simulation_id = await save_simulation_to_db(db_session, simulation_result)
            return simulation_result, simulation_id

    simulation_result, simulation_id = asyncio.run(_simulate_and_save())
    click.echo(
        f"Simulation result: {simulation_result.profit_pct * 100:2.2f}%, {simulation_result.profit:2.2f}"
    )
    click.echo(f"Simulation saved to database with ID: {simulation_id}")


# =============================================================================
# Datasource Commands
# =============================================================================


@cli.command(
    "fetch-data",
    help="Refresh all market data: constituents, index prices, and stock prices for SP500 and NASDAQ.",
)
def fetch_data():
    click.echo("Refreshing all market data (SP500 + NASDAQ)...")
    asyncio.run(datasource_service.refresh_all())
    click.echo("Done")


@cli.command(
    "fetch-prices", help="Fetch stock prices for all current constituents of an index."
)
@click.option(
    "--index",
    "-i",
    type=click.Choice([member.value for member in StockIndex]),
    required=False,
    default=StockIndex.SP500.value,
    help="Stock index",
)
def fetch_prices(index: str):
    stock_index = StockIndex(index)
    click.echo(f"Fetching stock prices for {stock_index.value} constituents")

    async def _run():
        async with conn.get_db_session() as db_session:
            return await datasource_service.fetch_stock_prices(db_session, stock_index)

    results = asyncio.run(_run())
    fetched = sum(1 for v in results.values() if v > 0)
    click.echo(f"Done: {fetched} symbols fetched, {len(results) - fetched} skipped")


@cli.command("fetch-index", help="Fetch index price history.")
@click.option(
    "--index",
    "-i",
    type=click.Choice([member.value for member in StockIndex]),
    required=False,
    default=StockIndex.SP500.value,
    help="Stock index",
)
def fetch_index(index: str):
    stock_index = StockIndex(index)
    click.echo(f"Fetching index prices for {stock_index.value}")

    async def _run():
        async with conn.get_db_session() as db_session:
            return await datasource_service.fetch_index_prices(db_session, stock_index)

    count = asyncio.run(_run())
    click.echo(f"Done: {count} price records saved")


@cli.command(
    "fetch-constituents", help="Fetch constituent change history for an index."
)
@click.option(
    "--index",
    "-i",
    type=click.Choice([member.value for member in StockIndex]),
    required=False,
    default=StockIndex.SP500.value,
    help="Stock index",
)
def fetch_constituents(index: str):
    stock_index = StockIndex(index)
    click.echo(f"Fetching constituent changes for {stock_index.value}")

    async def _run():
        async with conn.get_db_session() as db_session:
            return await datasource_service.fetch_constituent_changes(
                db_session, stock_index
            )

    count = asyncio.run(_run())
    click.echo(f"Done: {count} constituent changes saved")


# =============================================================================
# Agent Commands
# =============================================================================


@cli.command(
    "agent", help="Run the AI strategy agent with a natural language instruction."
)
@click.option(
    "--instruction",
    "-i",
    type=str,
    required=True,
    help="Strategy idea in natural language",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default="claude-sonnet-4-20250514",
    help="Anthropic model to use",
)
def agent(instruction: str, model: str):
    from stockidea.agent.agent import run_agent

    click.echo("Starting AI strategy agent...")
    click.echo(f"Instruction: {instruction}")
    click.echo(f"Model: {model}")
    click.echo("---")

    final_response = asyncio.run(run_agent(instruction=instruction, model=model))

    click.echo("---")
    click.echo("Final recommendation:")
    click.echo(final_response)


if __name__ == "__main__":
    cli()
