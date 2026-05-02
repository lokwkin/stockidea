"""Telegram bot service — long-running listener for personal trading commands.

Listens for ``/pick`` from the configured chat and replies with the screener's
buy/sell recommendation against the portfolio supplied in the message.
"""

import html
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from stockidea import constants
from stockidea.datasource.database import conn
from stockidea.rule_engine import DEFAULT_SORT, compile_rule, compile_sort
from stockidea.screener import service as screener_service
from stockidea.screener.types import Holding, Portfolio, ScreenerResult
from stockidea.types import StockIndex, StockIndicators, StopLossConfig

logger = logging.getLogger(__name__)


_USAGE_TEXT = (
    "Send /pick with optional inline overrides + portfolio, e.g.:\n\n"
    "/pick 5 NASDAQ $:10000 AAPL:5 MSFT:10\n\n"
    "Tokens (any order, all optional):\n"
    "  N            max stocks (default from STRATEGY_MAX_STOCKS)\n"
    "  SP500|NASDAQ index (default from STRATEGY_INDEX)\n"
    "  $:N          cash available\n"
    "  SYMBOL:QTY   current holding\n"
)


class _Strategy:
    """Pre-compiled strategy bundle — built once at bot startup from env vars."""

    def __init__(
        self,
        rule_str: str,
        rule_func: Callable[[StockIndicators], bool],
        sort_str: str,
        sort_func: Callable[[StockIndicators], float],
        max_stocks: int,
        from_index: StockIndex,
        stop_loss: StopLossConfig | None,
    ):
        self.rule_str = rule_str
        self.rule_func = rule_func
        self.sort_str = sort_str
        self.sort_func = sort_func
        self.max_stocks = max_stocks
        self.from_index = from_index
        self.stop_loss = stop_loss


def _build_strategy() -> _Strategy:
    if not constants.STRATEGY_RULE:
        raise RuntimeError("STRATEGY_RULE env var is required to run the Telegram bot")
    rule_str = constants.STRATEGY_RULE
    sort_str = constants.STRATEGY_SORT or DEFAULT_SORT
    stop_loss = (
        StopLossConfig(expression=constants.STRATEGY_STOP_LOSS_EXPR)
        if constants.STRATEGY_STOP_LOSS_EXPR
        else None
    )
    return _Strategy(
        rule_str=rule_str,
        rule_func=compile_rule(rule_str),
        sort_str=sort_str,
        sort_func=compile_sort(sort_str),
        max_stocks=constants.STRATEGY_MAX_STOCKS,
        from_index=StockIndex(constants.STRATEGY_INDEX),
        stop_loss=stop_loss,
    )


@dataclass
class _PickArgs:
    portfolio: Portfolio
    has_holdings: bool
    max_stocks: int | None  # None ⇒ use strategy default
    from_index: StockIndex | None  # None ⇒ use strategy default


_INDEX_TOKENS = {idx.value: idx for idx in StockIndex}


def _parse_pick_args(text: str) -> _PickArgs:
    """Parse the args following ``/pick`` into a ``_PickArgs``.

    Format: space-delimited tokens on one line, e.g.
    ``/pick 5 NASDAQ $:10000 GEV:20``.

    Token forms (all optional, any order):
      ``N``            integer ⇒ max_stocks override
      ``SP500|NASDAQ`` index override
      ``$:N``          cash
      ``SYMBOL:QTY``   holding

    Anything malformed raises ``ValueError`` — the caller turns that into a
    friendly reply.
    """
    cash: float = 0.0
    holdings: list[Holding] = []
    has_holdings = False
    max_stocks: int | None = None
    from_index: StockIndex | None = None
    # Skip the first token (the /pick command itself).
    for token in text.split()[1:]:
        if ":" in token:
            prefix, _, value = token.partition(":")
            prefix = prefix.strip()
            value = value.strip()
            if prefix == "$":
                try:
                    cash = float(value)
                except ValueError:
                    raise ValueError(f"cash must be a number, got '{value}'")
                continue
            try:
                qty = int(value)
            except ValueError:
                raise ValueError(f"quantity must be an integer, got '{value}'")
            try:
                holdings.append(Holding(symbol=prefix.upper(), quantity=qty))
            except ValueError as e:
                raise ValueError(f"invalid holding {prefix}: {e}")
            has_holdings = True
            continue
        upper = token.upper()
        if upper in _INDEX_TOKENS:
            from_index = _INDEX_TOKENS[upper]
            continue
        if token.isdigit():
            max_stocks = int(token)
            continue
        raise ValueError(
            f"unrecognised token '{token}' "
            f"— expected N, SP500/NASDAQ, $:N, or SYMBOL:QTY"
        )
    return _PickArgs(
        portfolio=Portfolio(cash=cash, holdings=holdings),
        has_holdings=has_holdings,
        max_stocks=max_stocks,
        from_index=from_index,
    )


def _format_stop_loss(stop_loss: StopLossConfig | None) -> str:
    if stop_loss is None:
        return "(none)"
    return f"<code>{html.escape(stop_loss.expression)}</code>"


def _format_pick_line(
    symbol: str,
    quantity: int | None,
    price: float | None,
    stop_loss_price: float | None,
    show_quantity: bool,
) -> str:
    qty_to_show = quantity if show_quantity else None
    if price is not None:
        head = (
            f"<b>{symbol}</b> {qty_to_show}@${price:.2f}"
            if qty_to_show is not None
            else f"<b>{symbol}</b> @${price:.2f}"
        )
    else:
        head = (
            f"<b>{symbol}</b> {qty_to_show}"
            if qty_to_show is not None
            else f"<b>{symbol}</b>"
        )
    parts = [head]
    if stop_loss_price is not None:
        parts.append(f"Stop at ${stop_loss_price:.2f}")
    return "  • " + " ".join(parts)


def _format_screener_result(
    result: ScreenerResult,
    *,
    rule_str: str,
    sort_str: str,
    stop_loss: StopLossConfig | None,
    max_stocks: int,
    from_index: StockIndex,
    show_orders: bool,
) -> str:
    lines: list[str] = []
    lines.append(f"📊 <b>Screener Result for {datetime.now().strftime('%Y-%m-%d')}</b>")
    lines.append("")
    lines.append(f"Index: <b>{from_index.value}</b>")
    lines.append(f"Max stocks: <b>{max_stocks}</b>")
    lines.append(f"Rule: <code>{html.escape(rule_str)}</code>")
    lines.append(f"Sort: <code>{html.escape(sort_str)}</code>")
    lines.append(f"Stop loss: {_format_stop_loss(stop_loss)}")
    lines.append("")
    lines.append("Picks:")
    if not result.picks:
        lines.append("  (no stocks passed the rule)")
    else:
        for p in result.picks:
            lines.append(
                _format_pick_line(
                    p.symbol,
                    p.target_quantity,
                    p.buy_price,
                    p.stop_loss_price,
                    show_quantity=show_orders,
                )
            )

    if show_orders:
        lines.append("")
        lines.append("🔴 Sell:")
        if not result.sells:
            lines.append("  (none)")
        else:
            for s in result.sells:
                lines.append(
                    _format_pick_line(
                        s.symbol, s.quantity, s.price, None, show_quantity=True
                    )
                )

        lines.append("")
        lines.append("🟢 Buy:")
        if not result.buys:
            lines.append("  (none)")
        else:
            for b in result.buys:
                lines.append(
                    _format_pick_line(
                        b.symbol,
                        b.quantity,
                        b.price,
                        b.stop_loss_price,
                        show_quantity=True,
                    )
                )
    return "\n".join(lines)


def _is_authorized(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    return str(chat.id) == constants.TELEGRAM_CHAT_ID


async def _handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    if update.message is None:
        return
    await update.message.reply_text(_USAGE_TEXT)


def _make_pick_handler(strategy: _Strategy):
    async def _handle_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not _is_authorized(update):
            logger.warning(
                "Ignoring /pick from unauthorized chat id=%s",
                update.effective_chat.id if update.effective_chat else "?",
            )
            return
        if update.message is None or update.message.text is None:
            return

        try:
            args = _parse_pick_args(update.message.text)
        except ValueError as e:
            await update.message.reply_text(
                f"⚠️ Couldn't parse your message: {e}\n\n{_USAGE_TEXT}"
            )
            return

        max_stocks = (
            args.max_stocks if args.max_stocks is not None else strategy.max_stocks
        )
        from_index = (
            args.from_index if args.from_index is not None else strategy.from_index
        )

        try:
            now = datetime.now()
            async with conn.get_db_session() as db_session:
                result = await screener_service.pick(
                    db_session,
                    indicators_date=screener_service.default_indicators_cutoff(now),
                    buy_date=now,
                    rule_func=strategy.rule_func,
                    sort_func=strategy.sort_func,
                    max_stocks=max_stocks,
                    from_index=from_index,
                    stop_loss=strategy.stop_loss,
                    portfolio=args.portfolio,
                )
        except Exception as e:
            logger.exception("screener.pick failed")
            await update.message.reply_text(f"⚠️ Screener failed: {e}")
            return

        await update.message.reply_text(
            _format_screener_result(
                result,
                rule_str=strategy.rule_str,
                sort_str=strategy.sort_str,
                stop_loss=strategy.stop_loss,
                max_stocks=max_stocks,
                from_index=from_index,
                show_orders=args.has_holdings,
            ),
            parse_mode=ParseMode.HTML,
        )

    return _handle_pick


def run_bot() -> None:
    """Start the Telegram bot. Blocks until the process is interrupted."""
    if not constants.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    if not constants.TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set")

    strategy = _build_strategy()
    logger.info(
        "Starting Telegram bot for chat_id=%s, index=%s, max_stocks=%d",
        constants.TELEGRAM_CHAT_ID,
        strategy.from_index.value,
        strategy.max_stocks,
    )

    app = Application.builder().token(constants.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", _handle_start))
    app.add_handler(CommandHandler("pick", _make_pick_handler(strategy)))
    app.run_polling()
