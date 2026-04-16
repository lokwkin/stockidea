"""CLI commands for indicator operations."""

import asyncio
import logging
from datetime import datetime, timedelta

import click

from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import conn
from stockidea.indicators import service as indicators_service
from stockidea.rule_engine import compile_rule
from stockidea.types import StockIndex, StockIndicators

logger = logging.getLogger(__name__)


async def _compute(date: datetime, index: StockIndex) -> list[StockIndicators]:
    async with conn.get_db_session() as db_session:
        symbols = await datasource_service.get_constituent_at(
            db_session, index, date.date()
        )
        stock_indicators_batch = await indicators_service.get_stock_indicators_batch(
            db_session,
            symbols=symbols,
            indicators_date=date,
            back_period_weeks=52,
            compute_if_not_exists=True,
        )
        return stock_indicators_batch


def _iter_fridays(start: datetime, end: datetime):
    """Yield Fridays from start to end (inclusive)."""
    # Move to the first Friday on or after start
    days_until_friday = (4 - start.weekday()) % 7
    current = start + timedelta(days=days_until_friday)
    while current <= end:
        yield current
        current += timedelta(weeks=1)


@click.group("indicators")
def indicators_cli():
    """Indicator computation commands."""
    pass


@indicators_cli.command(
    "compute",
    help="Compute stock indicators for a given date or date range. "
    "When a range is given, computes for each Friday within the range.",
)
@click.option(
    "--date",
    "-d",
    type=str,
    required=False,
    default=None,
    help="Single indicator date in YYYY-MM-DD format (default: today)",
)
@click.option(
    "--date-start",
    type=str,
    required=False,
    default=None,
    help="Start date for range computation (YYYY-MM-DD)",
)
@click.option(
    "--date-end",
    type=str,
    required=False,
    default=None,
    help="End date for range computation (YYYY-MM-DD)",
)
@click.option(
    "--index",
    "-i",
    type=click.Choice([member.value for member in StockIndex]),
    required=False,
    default=StockIndex.SP500.value,
    help="Stock index to compute indicators for",
)
def compute(date: str | None, date_start: str | None, date_end: str | None, index: str):
    stock_index = StockIndex(index)

    # Validate mutually exclusive options
    if date and (date_start or date_end):
        raise click.BadParameter(
            "Use either --date for a single date or --date-start/--date-end for a range, not both."
        )

    if date_start or date_end:
        # Range mode
        if not date_start or not date_end:
            raise click.BadParameter(
                "Both --date-start and --date-end are required for range computation."
            )
        try:
            start = datetime.strptime(date_start, "%Y-%m-%d")
            end = datetime.strptime(date_end, "%Y-%m-%d")
        except ValueError:
            raise click.BadParameter("Invalid date format. Use YYYY-MM-DD format.")

        if start >= end:
            raise click.BadParameter("--date-start must be before --date-end")

        fridays = list(_iter_fridays(start, end))
        click.echo(
            f"Computing indicators for {len(fridays)} Fridays from {start.date()} to {end.date()}"
        )

        async def _compute_range():
            for i, friday in enumerate(fridays, 1):
                click.echo(f"[{i}/{len(fridays)}] Computing {friday.date()}...")
                await _compute(date=friday, index=stock_index)

        asyncio.run(_compute_range())
        click.echo("Done")
    else:
        # Single date mode
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        try:
            date_parsed = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise click.BadParameter(
                f"Invalid date format: {date_str}. Use YYYY-MM-DD format."
            )
        asyncio.run(_compute(date=date_parsed, index=stock_index))


@indicators_cli.command(
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

    try:
        rule_func = compile_rule(rule)
    except Exception as e:
        raise click.BadParameter(f"Invalid rule expression: {e}")

    stock_indicators_batch = asyncio.run(_compute(date=date_parsed, index=stock_index))

    filtered_stocks = indicators_service.apply_rule(
        indicators_batch=stock_indicators_batch, rule_func=rule_func
    )

    selected_stocks = filtered_stocks[:max_stocks]
    logger.info(
        f"Selected: {[stock.symbol for stock in selected_stocks]} (from {len(filtered_stocks)} filtered)"
    )
