"""Telegram bot service — long-running listener for personal trading commands.

Listens for ``/pick`` from the configured chat and replies with the screener's
buy/sell recommendation against the portfolio supplied in the message.
"""

import logging
from datetime import datetime
from typing import Callable

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from stockidea import constants
from stockidea.datasource.database import conn
from stockidea.rule_engine import DEFAULT_SORT, compile_rule, compile_sort
from stockidea.screener import service as screener_service
from stockidea.screener.types import Holding, Portfolio, ScreenerResult
from stockidea.types import StockIndex, StockIndicators, StopLossConfig

logger = logging.getLogger(__name__)


_USAGE_TEXT = (
    "Send /pick with your portfolio inline, e.g.:\n\n"
    "/pick $:10000 AAPL:5 MSFT:10\n\n"
    "Use $:N for cash and SYMBOL:QTY for each holding. Both are optional — "
    "I'll reply with picks based on the configured strategy."
)


class _Strategy:
    """Pre-compiled strategy bundle — built once at bot startup from env vars."""

    def __init__(
        self,
        rule_func: Callable[[StockIndicators], bool],
        sort_func: Callable[[StockIndicators], float],
        max_stocks: int,
        from_index: StockIndex,
        stop_loss: StopLossConfig | None,
    ):
        self.rule_func = rule_func
        self.sort_func = sort_func
        self.max_stocks = max_stocks
        self.from_index = from_index
        self.stop_loss = stop_loss


def _build_strategy() -> _Strategy:
    if not constants.STRATEGY_RULE:
        raise RuntimeError("STRATEGY_RULE env var is required to run the Telegram bot")
    rule_func = compile_rule(constants.STRATEGY_RULE)
    sort_func = compile_sort(constants.STRATEGY_SORT or DEFAULT_SORT)
    stop_loss = StopLossConfig.parse_options(
        pct=float(constants.STRATEGY_STOP_LOSS_PCT)
        if constants.STRATEGY_STOP_LOSS_PCT
        else None,
        ma_spec=constants.STRATEGY_STOP_LOSS_MA or None,
    )
    return _Strategy(
        rule_func=rule_func,
        sort_func=sort_func,
        max_stocks=constants.STRATEGY_MAX_STOCKS,
        from_index=StockIndex(constants.STRATEGY_INDEX),
        stop_loss=stop_loss,
    )


def _parse_portfolio_message(text: str) -> tuple[Portfolio, bool]:
    """Parse the args following ``/pick`` into ``(Portfolio, has_holdings)``.

    Format: space-delimited tokens on one line, e.g. ``/pick $:10000 GEV:20``.
    ``$:N`` sets cash; ``SYMBOL:QTY`` adds a holding. Both are optional.
    Anything malformed raises ``ValueError`` — the caller turns that into a
    friendly reply.
    """
    cash: float = 0.0
    holdings: list[Holding] = []
    has_holdings = False
    # Skip the first token (the /pick command itself).
    for token in text.split()[1:]:
        if ":" not in token:
            raise ValueError(f"expected '$:N' or 'SYMBOL:QTY', got '{token}'")
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
    return Portfolio(cash=cash, holdings=holdings), has_holdings


def _format_pick_line(
    symbol: str,
    quantity: int | None,
    price: float | None,
    stop_loss_price: float | None,
) -> str:
    if price is not None:
        head = (
            f"{symbol} {quantity}@${price:.2f}"
            if quantity is not None
            else f"{symbol} @${price:.2f}"
        )
    else:
        head = f"{symbol} {quantity}" if quantity is not None else symbol
    parts = [head, "lmt/mkt"]
    if stop_loss_price is not None:
        parts.append(f"stop @${stop_loss_price:.2f}")
    return "  • " + " ".join(parts)


def _format_screener_result(result: ScreenerResult, show_orders: bool) -> str:
    lines: list[str] = []
    lines.append("📊 Screener Result")
    lines.append("")
    lines.append("Picks:")
    if not result.picks:
        lines.append("  (no stocks passed the rule)")
    else:
        for p in result.picks:
            lines.append(
                _format_pick_line(
                    p.symbol, p.target_quantity, p.buy_price, p.stop_loss_price
                )
            )

    if show_orders:
        lines.append("")
        lines.append("🔴 Sell:")
        if not result.sells:
            lines.append("  (none)")
        else:
            for s in result.sells:
                lines.append(_format_pick_line(s.symbol, s.quantity, s.price, None))

        lines.append("")
        lines.append("🟢 Buy:")
        if not result.buys:
            lines.append("  (none)")
        else:
            for b in result.buys:
                lines.append(
                    _format_pick_line(b.symbol, b.quantity, b.price, b.stop_loss_price)
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
            portfolio, has_holdings = _parse_portfolio_message(update.message.text)
        except ValueError as e:
            await update.message.reply_text(
                f"⚠️ Couldn't parse your portfolio: {e}\n\n{_USAGE_TEXT}"
            )
            return

        try:
            now = datetime.now()
            async with conn.get_db_session() as db_session:
                result = await screener_service.pick(
                    db_session,
                    indicators_date=screener_service.default_indicators_cutoff(now),
                    buy_date=now,
                    rule_func=strategy.rule_func,
                    sort_func=strategy.sort_func,
                    max_stocks=strategy.max_stocks,
                    from_index=strategy.from_index,
                    stop_loss=strategy.stop_loss,
                    portfolio=portfolio,
                )
        except Exception as e:
            logger.exception("screener.pick failed")
            await update.message.reply_text(f"⚠️ Screener failed: {e}")
            return

        await update.message.reply_text(
            _format_screener_result(result, show_orders=has_holdings)
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
