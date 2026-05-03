"""Screener service — pick stocks for a date and (optionally) size against a portfolio."""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from math import floor
from typing import Callable

from simpleeval import SimpleEval  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.datasource import service as datasource_service
from stockidea.helper import previous_friday
from stockidea.indicators import service as indicators_service
from stockidea.rule_engine import SAFE_FUNCTIONS
from stockidea.screener.types import (
    OrderItem,
    Pick,
    Portfolio,
    ScreenerResult,
)
from stockidea.types import (
    STOP_LOSS_EXPR_SMA_PERIODS,
    StockIndex,
    StockIndicators,
    StopLossConfig,
)

logger = logging.getLogger(__name__)


def _referenced_sma_periods(expression: str) -> list[int]:
    """Return the SMA periods (e.g. 50) referenced as ``sma_NN`` in the expression."""
    found = {int(m) for m in re.findall(r"\bsma_(\d+)\b", expression)}
    return sorted(p for p in STOP_LOSS_EXPR_SMA_PERIODS if p in found)


async def resolve_stop_loss_price(
    db_session: AsyncSession,
    symbol: str,
    buy_date: datetime,
    buy_price: float,
    stop_loss: StopLossConfig,
) -> float | None:
    """Compute a per-position stop-loss price by evaluating the expression.

    Context exposes ``buy_price`` and ``sma_20``/``sma_50``/``sma_100``/``sma_200``
    (prior trading day's SMA — never includes ``buy_date``'s close, which would be
    lookahead at the moment of the Monday-open fill). Returns ``None`` when:

    - a referenced SMA is unavailable for the symbol/date,
    - the expression fails to evaluate, or
    - the resulting stop price is ``>= buy_price`` (an above-buy stop would
      fire immediately on day 1 and produce phantom profit).
    """
    needed_periods = _referenced_sma_periods(stop_loss.expression)
    sma_lookup_date = (buy_date - timedelta(days=1)).date()
    sma_values = await asyncio.gather(
        *[
            datasource_service.get_sma_at_date(db_session, symbol, p, sma_lookup_date)
            for p in needed_periods
        ]
    )
    context: dict[str, float] = {"buy_price": buy_price}
    for period, value in zip(needed_periods, sma_values):
        if value is None or value <= 0:
            logger.warning(
                f"SMA({period}) unavailable for {symbol} on/before {sma_lookup_date}; "
                f"skipping stop loss for this position"
            )
            return None
        context[f"sma_{period}"] = value

    try:
        result = SimpleEval(names=context, functions=SAFE_FUNCTIONS).eval(
            stop_loss.expression
        )
        stop_price = float(result)
    except Exception as e:
        logger.warning(
            f"Stop-loss expression {stop_loss.expression!r} failed to evaluate "
            f"for {symbol} on {buy_date.date()}: {e}; skipping stop loss"
        )
        return None

    if stop_price >= buy_price:
        logger.warning(
            f"Stop-loss expression {stop_loss.expression!r} produced "
            f"${stop_price:.2f} >= buy_price ${buy_price:.2f} for {symbol} on "
            f"{buy_date.date()}; rejecting stop loss for this position"
        )
        return None
    return stop_price


async def _lookup_buy_price(
    db_session: AsyncSession, symbol: str, buy_date: datetime
) -> float:
    """Return the buy price (Monday-open convention) for a symbol on/near buy_date."""
    price_data = await datasource_service.get_stock_price_at_date(
        db_session, symbol, buy_date.date(), nearest=True
    )
    if price_data.open is None:
        raise ValueError(
            f"No open price for {symbol} on/near {buy_date.date()} — "
            "cannot apply Monday-open buy convention"
        )
    return price_data.open


async def _select_top_n(
    db_session: AsyncSession,
    indicators_date: datetime,
    constituent_date: datetime,
    rule_func: Callable[[StockIndicators], bool],
    sort_func: Callable[[StockIndicators], float] | None,
    max_stocks: int,
    from_index: StockIndex,
) -> list[StockIndicators]:
    """Filter + sort constituents and return the top-N indicators rows."""
    symbols = await datasource_service.get_constituent_at(
        db_session, from_index, constituent_date.date()
    )
    indicators_batch = await indicators_service.get_stock_indicators_batch(
        db_session,
        symbols=symbols,
        indicators_date=indicators_date,
        back_period_weeks=52,
        compute_if_not_exists=True,
    )
    filtered = indicators_service.apply_rule(
        indicators_batch, rule_func=rule_func, sort_func=sort_func
    )
    return filtered[:max_stocks]


async def pick(
    db_session: AsyncSession,
    *,
    indicators_date: datetime,
    buy_date: datetime | None = None,
    rule_func: Callable[[StockIndicators], bool],
    sort_func: Callable[[StockIndicators], float] | None,
    max_stocks: int,
    from_index: StockIndex,
    stop_loss: StopLossConfig | None = None,
    portfolio: Portfolio | None = None,
) -> ScreenerResult:
    """Pick top-N stocks for ``indicators_date``; optionally size + diff against a portfolio.

    - ``indicators_date``: indicator/Friday cutoff used for filtering+sorting.
    - ``buy_date``: date used for buy-price lookup (defaults to ``indicators_date``).
      Backtester passes the rebalance Monday here; screener CLI passes the same date.
    - ``portfolio``: when given, picks get a ``target_quantity`` based on equal-weight
      allocation of (cash + current liquidation value), and the result includes
      ``buys``/``sells`` order deltas against current holdings.
    """
    if buy_date is None:
        buy_date = indicators_date

    selected = await _select_top_n(
        db_session,
        indicators_date=indicators_date,
        constituent_date=buy_date,
        rule_func=rule_func,
        sort_func=sort_func,
        max_stocks=max_stocks,
        from_index=from_index,
    )
    logger.info(
        f"Screener selected {len(selected)} stock(s) for {indicators_date.date()}: "
        f"{[s.symbol for s in selected]}"
    )

    picks: list[Pick] = []
    for stock in selected:
        buy_price = await _lookup_buy_price(db_session, stock.symbol, buy_date)
        stop_loss_price = (
            await resolve_stop_loss_price(
                db_session, stock.symbol, buy_date, buy_price, stop_loss
            )
            if stop_loss is not None
            else None
        )
        picks.append(
            Pick(
                symbol=stock.symbol,
                indicators=stock,
                buy_price=buy_price,
                target_quantity=None,
                stop_loss_price=stop_loss_price,
            )
        )

    if portfolio is None:
        return ScreenerResult(picks=picks)

    # Portfolio mode: liquidate everything in concept, redistribute equally.
    holding_prices: dict[str, float] = {}
    total_value = portfolio.cash
    for holding in portfolio.holdings:
        price_data = await datasource_service.get_stock_price_at_date(
            db_session, holding.symbol, buy_date.date(), nearest=True
        )
        # Prefer open (matches buy convention); fall back to adj_close for valuation.
        held_price = (
            price_data.open if price_data.open is not None else price_data.adj_close
        )
        holding_prices[holding.symbol] = held_price
        total_value += holding.quantity * held_price

    if picks:
        allocation = total_value / len(picks)
        for p in picks:
            p.target_quantity = floor(allocation / p.buy_price)

    holdings_dict = {h.symbol: h.quantity for h in portfolio.holdings}
    picks_by_symbol = {p.symbol: p for p in picks}

    sells: list[OrderItem] = []
    for symbol, held_qty in holdings_dict.items():
        target = (
            picks_by_symbol[symbol].target_quantity if symbol in picks_by_symbol else 0
        )
        target = target or 0
        if target < held_qty:
            sells.append(
                OrderItem(
                    symbol=symbol,
                    quantity=held_qty - target,
                    price=holding_prices.get(symbol),
                )
            )

    buys: list[OrderItem] = []
    for p in picks:
        target = p.target_quantity or 0
        held = holdings_dict.get(p.symbol, 0)
        if target > held:
            buys.append(
                OrderItem(
                    symbol=p.symbol,
                    quantity=target - held,
                    price=p.buy_price,
                    stop_loss_price=p.stop_loss_price,
                )
            )

    return ScreenerResult(picks=picks, sells=sells, buys=buys)


def default_indicators_cutoff(reference_date: datetime) -> datetime:
    """Return the indicator/Friday cutoff to use given a reference date.

    Used by the bot and any caller wanting "the most recently available weekly
    indicator snapshot relative to today" — never lookahead into ``reference_date``.
    """
    return previous_friday(reference_date)
