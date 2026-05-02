"""CLI commands for backtest operations."""

import asyncio
from datetime import datetime
from typing import cast

import click

from stockidea.backtest.backtester import Backtester
from stockidea.datasource.database import conn
from stockidea.datasource.database.queries import (
    save_backtest_result as save_backtest_to_db,
)
from stockidea.rule_engine import DEFAULT_SORT, compile_rule, compile_sort
from stockidea.types import (
    SellTiming,
    StockIndex,
    StopLossConfig,
)

_SELL_TIMING_CHOICES = ("friday_close", "monday_open")


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
    "--sort",
    "-s",
    "sort_expr",
    type=str,
    default=DEFAULT_SORT,
    help=f"Sort expression for stock selection (default: '{DEFAULT_SORT}')",
)
@click.option(
    "--stop-loss-expr",
    type=str,
    default=None,
    help="Stop-loss expression, evaluated at buy time. Vars: 'buy_price', "
    "'sma_20', 'sma_50', 'sma_100', 'sma_200' (prior trading day). Examples: "
    "'buy_price * 0.95' (5%% below buy), 'sma_50 * 0.95' (95%% of SMA50 at buy). "
    "Stops with stop_price >= buy_price are rejected per-position.",
)
@click.option(
    "--sell-timing",
    type=click.Choice(list(_SELL_TIMING_CHOICES)),
    default="friday_close",
    show_default=True,
    help="When to sell at end of holding period: 'friday_close' = previous "
    "Friday's adjusted close (weekend gap before next buy); 'monday_open' = "
    "next-rebalance Monday's open (continuous capital, no weekend gap).",
)
@click.option(
    "--slippage-pct",
    type=float,
    default=0.5,
    show_default=True,
    help="Per-fill slippage friction (% of price). Applied symmetrically: buys "
    "fill above the open, period-end sells below the close, and stop-loss "
    "exits below the stop trigger. Same friction applies to the baseline.",
)
def backtest(
    max_stocks: int,
    rebalance_interval_weeks: int,
    date_start: str,
    date_end: str,
    rule: str,
    index: str,
    sort_expr: str,
    stop_loss_expr: str | None,
    sell_timing: str,
    slippage_pct: float,
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
        sort_func = compile_sort(sort_expr)
    except Exception as e:
        raise click.BadParameter(f"Invalid sort expression: {e}")

    try:
        stop_loss = (
            StopLossConfig(expression=stop_loss_expr)
            if stop_loss_expr is not None
            else None
        )
    except ValueError as e:
        raise click.BadParameter(f"Invalid --stop-loss-expr: {e}")

    click.echo(
        f"Running backtest from {date_start_parsed.date()} to {date_end_parsed.date()}"
    )
    click.echo(
        f"Max stocks: {max_stocks}, Rebalance interval: {rebalance_interval_weeks} weeks"
    )
    click.echo(f"Rule: {rule}")
    click.echo(f"Sort: {sort_expr}")
    click.echo(f"Stock index: {stock_index}")
    click.echo(f"Sell timing: {sell_timing}")
    click.echo(f"Slippage: {slippage_pct}% per fill")
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
                sort_func=sort_func,
                sort_raw=sort_expr,
                stop_loss=stop_loss,
                sell_timing=cast(SellTiming, sell_timing),
                slippage_pct=slippage_pct,
            )
            backtest_result = await backtester.backtest()
            backtest_id = await save_backtest_to_db(db_session, backtest_result)
            return backtest_result, backtest_id

    backtest_result, backtest_id = asyncio.run(_backtest_and_save())
    click.echo(
        f"Backtest result: {backtest_result.profit_pct:2.2f}%, {backtest_result.profit:2.2f}"
    )
    click.echo(f"Backtest saved to database with ID: {backtest_id}")
