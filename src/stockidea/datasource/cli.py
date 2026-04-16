"""CLI commands for datasource operations."""

import asyncio
import click

from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn
from stockidea.types import StockIndex


@click.group("datasource")
def datasource_cli():
    """Data fetching commands."""
    pass


@datasource_cli.command(
    "fetch-data",
    help="Refresh all market data: constituents, index prices, and stock prices for SP500 and NASDAQ.",
)
def fetch_data():
    click.echo("Refreshing all market data (SP500 + NASDAQ)...")
    asyncio.run(datasource_service.refresh_all())
    click.echo("Done")


@datasource_cli.command(
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


@datasource_cli.command("fetch-index", help="Fetch index price history.")
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


@datasource_cli.command(
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
