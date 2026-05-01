"""CLI commands for backtest operations."""

import asyncio
from datetime import datetime

import click

from stockidea.backtest.backtester import Backtester
from stockidea.datasource.database import conn
from stockidea.datasource.database.queries import (
    save_backtest_result as save_backtest_to_db,
)
from stockidea.rule_engine import DEFAULT_RANKING, compile_ranking, compile_rule
from stockidea.types import StockIndex, StopLossConfig, SUPPORTED_STOP_LOSS_MA_PERIODS


@click.group("backtest")
def backtest_cli():
    """Backtest commands."""
    pass


@backtest_cli.command(
    "backtest", help="Backtest investment strategy for a given date range."
)
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
    help="Backtest start date in YYYY-MM-DD format",
)
@click.option(
    "--date-end",
    type=str,
    required=True,
    help="Backtest end date in YYYY-MM-DD format",
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
    help="Rule expression string (e.g., 'change_pct_13w > 10 AND max_drop_pct_2w > 15')",
)
@click.option(
    "--ranking",
    type=str,
    default=DEFAULT_RANKING,
    help=f"Ranking expression for stock selection (default: '{DEFAULT_RANKING}')",
)
@click.option(
    "--stop-loss-pct",
    type=float,
    default=None,
    help="Stop loss as % below buy price (e.g. 5 = exit if price drops 5%%). "
    "Mutually exclusive with --stop-loss-ma.",
)
@click.option(
    "--stop-loss-ma",
    type=str,
    default=None,
    help="Stop loss as % of an MA at buy time, format 'PERIOD:PERCENT' "
    f"(e.g. '50:95' = stop at 95%% of MA50_at_buy). PERIOD must be one of "
    f"{list(SUPPORTED_STOP_LOSS_MA_PERIODS)}. Mutually exclusive with --stop-loss-pct.",
)
def backtest(
    max_stocks: int,
    rebalance_interval_weeks: int,
    date_start: str,
    date_end: str,
    rule: str,
    index: str,
    ranking: str,
    stop_loss_pct: float | None,
    stop_loss_ma: str | None,
):
    stock_index = StockIndex(index)
    try:
        date_start_parsed = datetime.strptime(date_start, "%Y-%m-%d")
        date_end_parsed = datetime.strptime(date_end, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter("Invalid date format. Use YYYY-MM-DD format.")

    if date_start_parsed >= date_end_parsed:
        raise click.BadParameter("date_start must be before date_end")

    try:
        rule_func = compile_rule(rule)
    except Exception as e:
        raise click.BadParameter(f"Invalid rule expression: {e}")

    try:
        ranking_func = compile_ranking(ranking)
    except Exception as e:
        raise click.BadParameter(f"Invalid ranking expression: {e}")

    if stop_loss_pct is not None and stop_loss_ma is not None:
        raise click.BadParameter(
            "--stop-loss-pct and --stop-loss-ma are mutually exclusive"
        )

    stop_loss: StopLossConfig | None = None
    if stop_loss_pct is not None:
        try:
            stop_loss = StopLossConfig(type="percent", value=stop_loss_pct)
        except ValueError as e:
            raise click.BadParameter(f"Invalid --stop-loss-pct: {e}")
    elif stop_loss_ma is not None:
        try:
            period_str, pct_str = stop_loss_ma.split(":", 1)
            stop_loss = StopLossConfig(
                type="ma_percent",
                ma_period=int(period_str),
                value=float(pct_str),
            )
        except (ValueError, TypeError) as e:
            raise click.BadParameter(
                f"Invalid --stop-loss-ma '{stop_loss_ma}' (expected 'PERIOD:PERCENT'): {e}"
            )

    click.echo(
        f"Running backtest from {date_start_parsed.date()} to {date_end_parsed.date()}"
    )
    click.echo(
        f"Max stocks: {max_stocks}, Rebalance interval: {rebalance_interval_weeks} weeks"
    )
    click.echo(f"Rule: {rule}")
    click.echo(f"Ranking: {ranking}")
    click.echo(f"Stock index: {stock_index}")
    if stop_loss is not None:
        click.echo(f"Stop loss: {stop_loss.model_dump()}")

    async def _backtest_and_save():
        async with conn.get_db_session() as db_session:
            backtester = Backtester(
                db_session=db_session,
                max_stocks=max_stocks,
                rebalance_interval_weeks=rebalance_interval_weeks,
                date_start=date_start_parsed,
                date_end=date_end_parsed,
                rule_func=rule_func,
                rule_raw=rule,
                from_index=stock_index,
                baseline_index=StockIndex.SP500,
                ranking_func=ranking_func,
                ranking_raw=ranking,
                stop_loss=stop_loss,
            )
            backtest_result = await backtester.backtest()
            backtest_id = await save_backtest_to_db(db_session, backtest_result)
            return backtest_result, backtest_id

    backtest_result, backtest_id = asyncio.run(_backtest_and_save())
    click.echo(
        f"Backtest result: {backtest_result.profit_pct:2.2f}%, {backtest_result.profit:2.2f}"
    )
    click.echo(f"Backtest saved to database with ID: {backtest_id}")
