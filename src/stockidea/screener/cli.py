"""CLI commands for the screener module."""

import asyncio
import logging
from datetime import datetime

import click

from stockidea.datasource.database import conn
from stockidea.rule_engine import DEFAULT_SORT, compile_rule, compile_sort
from stockidea.screener import service as screener_service
from stockidea.screener.types import Holding, Portfolio, ScreenerResult
from stockidea.types import StockIndex, StopLossConfig

logger = logging.getLogger(__name__)


def _parse_holding(spec: str) -> Holding:
    parts = spec.split(":", 1)
    if len(parts) != 2:
        raise click.BadParameter(f"Invalid --holding '{spec}' (expected 'SYMBOL:QTY')")
    symbol, qty_str = parts
    try:
        qty = int(qty_str)
    except ValueError:
        raise click.BadParameter(
            f"Invalid --holding '{spec}': quantity must be an integer"
        )
    try:
        return Holding(symbol=symbol.strip().upper(), quantity=qty)
    except ValueError as e:
        raise click.BadParameter(f"Invalid --holding '{spec}': {e}")


def _format_result(result: ScreenerResult, has_portfolio: bool) -> str:
    lines: list[str] = []
    lines.append("Picks:")
    if not result.picks:
        lines.append("  (no stocks passed the rule)")
    else:
        for p in result.picks:
            qty_str = (
                f" target_qty={p.target_quantity}"
                if p.target_quantity is not None
                else ""
            )
            stop_str = (
                f" stop=${p.stop_loss_price:.2f}"
                if p.stop_loss_price is not None
                else ""
            )
            lines.append(f"  {p.symbol}  buy=${p.buy_price:.2f}{qty_str}{stop_str}")

    if has_portfolio:
        lines.append("")
        lines.append("Sells:")
        if not result.sells:
            lines.append("  (none)")
        else:
            for s in result.sells:
                price_str = f" @ ${s.price:.2f}" if s.price is not None else ""
                lines.append(f"  {s.symbol}  qty={s.quantity}{price_str}")

        lines.append("")
        lines.append("Buys:")
        if not result.buys:
            lines.append("  (none)")
        else:
            for b in result.buys:
                price_str = f" @ ${b.price:.2f}" if b.price is not None else ""
                stop_str = (
                    f" stop=${b.stop_loss_price:.2f}"
                    if b.stop_loss_price is not None
                    else ""
                )
                lines.append(f"  {b.symbol}  qty={b.quantity}{price_str}{stop_str}")
    return "\n".join(lines)


@click.group("screener")
def screener_cli():
    """Screener commands — pick stocks based on rule + sort."""
    pass


@screener_cli.command(
    "pick",
    help="Pick top-N stocks by rule + sort; optionally size against a portfolio.",
)
@click.option(
    "--date",
    "-d",
    type=str,
    required=False,
    default=None,
    help="Reference date in YYYY-MM-DD (default: today). Used as both the indicator "
    "cutoff and the buy-price lookup date.",
)
@click.option(
    "--rule",
    "-r",
    type=str,
    required=True,
    help="Rule expression string (e.g., 'change_pct_13w > 10 AND max_drop_pct_2w < 15')",
)
@click.option(
    "--max-stocks",
    "-m",
    type=int,
    default=3,
    show_default=True,
    help="Maximum number of stocks to hold at once.",
)
@click.option(
    "--index",
    "-i",
    type=click.Choice([m.value for m in StockIndex]),
    default=StockIndex.SP500.value,
    show_default=True,
    help="Stock index to screen.",
)
@click.option(
    "--sort",
    "-s",
    "sort_expr",
    type=str,
    default=DEFAULT_SORT,
    show_default=True,
    help="Sort expression — picks the stocks with the highest score.",
)
@click.option(
    "--cash",
    type=float,
    default=None,
    help="Available cash for sizing. When given (along with optional --holding), "
    "screener returns target_quantity per pick and a buys/sells delta vs current "
    "holdings.",
)
@click.option(
    "--holding",
    "holdings",
    multiple=True,
    help="Current holding in 'SYMBOL:QTY' format (repeatable). Requires --cash.",
)
@click.option(
    "--stop-loss-expr",
    type=str,
    default=None,
    help="Stop-loss expression evaluated at buy time. Vars: 'buy_price', "
    "'sma_20', 'sma_50', 'sma_100', 'sma_200' (prior trading day). "
    "Examples: 'buy_price * 0.95', 'sma_50 * 0.95'. "
    "Stops with stop_price >= buy_price are rejected per-position.",
)
def pick_cmd(
    date: str | None,
    rule: str,
    max_stocks: int,
    index: str,
    sort_expr: str,
    cash: float | None,
    holdings: tuple[str, ...],
    stop_loss_expr: str | None,
):
    stock_index = StockIndex(index)
    date_str = date or datetime.now().strftime("%Y-%m-%d")
    try:
        date_parsed = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")

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

    if holdings and cash is None:
        raise click.BadParameter("--holding requires --cash")

    portfolio: Portfolio | None = None
    if cash is not None:
        try:
            portfolio = Portfolio(
                cash=cash,
                holdings=[_parse_holding(h) for h in holdings],
            )
        except ValueError as e:
            raise click.BadParameter(f"Invalid portfolio: {e}")

    async def _run() -> ScreenerResult:
        async with conn.get_db_session() as db_session:
            return await screener_service.pick(
                db_session,
                indicators_date=date_parsed,
                buy_date=date_parsed,
                rule_func=rule_func,
                sort_func=sort_func,
                max_stocks=max_stocks,
                from_index=stock_index,
                stop_loss=stop_loss,
                portfolio=portfolio,
            )

    result = asyncio.run(_run())
    click.echo(_format_result(result, has_portfolio=portfolio is not None))
