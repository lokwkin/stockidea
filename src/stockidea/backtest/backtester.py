from datetime import datetime, timedelta
from math import floor
import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.indicators import service as indicators_service
from stockidea.datasource import service as datasource_service
from stockidea.helper import next_monday, previous_friday
from stockidea.rule_engine import extract_involved_keys
from stockidea.backtest.scoring import compute_scores
from stockidea.types import (
    BacktestInvestment,
    BacktestRebalance,
    BacktestConfig,
    BacktestResult,
    StockIndex,
    StockIndicators,
    StopLossConfig,
)

logger = logging.getLogger(__name__)


class Backtester:
    db_session: AsyncSession
    initial_balance: float
    date_start: datetime
    date_end: datetime
    rebalance_interval_weeks: int
    max_stocks: int
    rule_func: Callable[[StockIndicators], bool]
    rule_raw: str
    ranking_func: Callable[[StockIndicators], float] | None
    ranking_raw: str
    stop_loss: StopLossConfig | None

    def __init__(
        self,
        db_session: AsyncSession,
        max_stocks: int,
        rebalance_interval_weeks: int,
        date_start: datetime,
        date_end: datetime,
        rule_func: Callable[[StockIndicators], bool],
        rule_raw: str,
        from_index: StockIndex,
        baseline_index: StockIndex,
        ranking_func: Callable[[StockIndicators], float],
        ranking_raw: str,
        stop_loss: StopLossConfig | None = None,
    ):
        self.db_session = db_session
        self.initial_balance = 10000
        self.max_stocks = max_stocks
        self.rebalance_interval_weeks = rebalance_interval_weeks
        self.date_start = date_start
        self.date_end = date_end
        self.rule_func = rule_func
        self.rule_raw = rule_raw
        self.from_index = from_index
        self.baseline_index = baseline_index
        self.ranking_func = ranking_func
        self.ranking_raw = ranking_raw
        self.stop_loss = stop_loss

    async def pick_stocks(self, today: datetime) -> list[StockIndicators]:
        # Compute indicators from data through last Friday's close. With the
        # Monday-open buy convention, the rebalance Monday's prices aren't
        # known when the picks are made — using `today` would be lookahead
        # (the weekly aggregator would bucket Monday's close as the latest
        # observation).
        cutoff = previous_friday(today)

        symbols = await datasource_service.get_constituent_at(
            self.db_session, self.from_index, today.date()
        )

        stock_indicators_batch = await indicators_service.get_stock_indicators_batch(
            self.db_session,
            symbols=symbols,
            indicators_date=cutoff,
            back_period_weeks=52,
            compute_if_not_exists=True,
        )

        filtered_stocks = indicators_service.apply_rule(
            stock_indicators_batch,
            rule_func=self.rule_func,
            ranking_func=self.ranking_func,
        )

        selected_stocks = filtered_stocks[: self.max_stocks]
        logger.info(
            f"Selected: {[stock.symbol for stock in selected_stocks]} (from {len(filtered_stocks)} filtered)"
        )

        return selected_stocks

    async def _resolve_stop_price(
        self, symbol: str, buy_date: datetime, buy_price: float
    ) -> float | None:
        """Compute the stop-loss price for a position, fixed at buy time.

        Returns None if no stop loss is configured, or if the required MA value is
        unavailable (in which case the position is held without a stop).
        """
        if self.stop_loss is None:
            return None
        if self.stop_loss.type == "percent":
            return buy_price * (1 - self.stop_loss.value / 100)
        # type == "ma_percent"
        assert self.stop_loss.ma_period is not None
        ma_value = await datasource_service.get_sma_at_date(
            self.db_session, symbol, self.stop_loss.ma_period, buy_date.date()
        )
        if ma_value is None or ma_value <= 0:
            logger.warning(
                f"SMA({self.stop_loss.ma_period}) unavailable for {symbol} on "
                f"{buy_date.date()}; skipping stop loss for this position"
            )
            return None
        return ma_value * (self.stop_loss.value / 100)

    async def _find_stop_loss_exit(
        self,
        symbol: str,
        buy_date: datetime,
        sell_date: datetime,
        stop_price: float,
    ) -> tuple[datetime, float] | None:
        """Scan daily prices between buy and sell. Return (exit_date, exit_price) on
        the first day whose intra-day low breaches `stop_price`, else None.

        Per assumption: when `low <= stop_price`, the position fills at exactly
        `stop_price` (no intra-day data, so this is a simplification).
        """
        prices = await datasource_service.get_stock_price_history(
            self.db_session,
            symbol,
            from_date=(buy_date + timedelta(days=1)).date(),
            to_date=sell_date.date(),
        )
        # get_stock_price_history returns desc-ordered; iterate ascending.
        for price in sorted(prices, key=lambda p: p.date):
            if price.low is not None and price.low <= stop_price:
                exit_dt = datetime.combine(price.date, buy_date.time())
                return exit_dt, stop_price
        return None

    async def invest(
        self, symbol: str, buy_date: datetime, sell_date: datetime, amount: float
    ) -> tuple[BacktestInvestment, float]:
        """Invest in a stock — buy at Monday open, sell at the prior Friday's close.

        `buy_date` is the rebalance Monday; `sell_date` is the next rebalance
        Monday. Real fill is the open of `buy_date` and the close of
        previous_friday(sell_date), with the weekend gap before the next buy.
        Returns (investment, uninvested_cash).
        """
        buy_price_data = await datasource_service.get_stock_price_at_date(
            self.db_session, symbol, buy_date.date(), nearest=True
        )
        if buy_price_data.open is None:
            raise ValueError(
                f"No open price for {symbol} on/near {buy_date.date()} — "
                "cannot apply Monday-open buy convention"
            )
        buy_stock_price = buy_price_data.open

        friday_sell_date = previous_friday(sell_date)
        sell_stock_price = (
            await datasource_service.get_stock_price_at_date(
                self.db_session, symbol, friday_sell_date.date(), nearest=True
            )
        ).adj_close
        actual_sell_date = friday_sell_date

        stop_price = await self._resolve_stop_price(symbol, buy_date, buy_stock_price)
        if stop_price is not None:
            exit_info = await self._find_stop_loss_exit(
                symbol, buy_date, friday_sell_date, stop_price
            )
            if exit_info is not None:
                actual_sell_date, sell_stock_price = exit_info
                logger.info(
                    f"Stop loss hit for {symbol}: exit {actual_sell_date.date()} "
                    f"@ {sell_stock_price:.2f} (stop={stop_price:.2f}, "
                    f"buy={buy_stock_price:.2f})"
                )

        position = floor(amount / buy_stock_price)
        uninvested = amount - position * buy_stock_price
        profit = (sell_stock_price - buy_stock_price) * position
        profit_pct = (sell_stock_price - buy_stock_price) / buy_stock_price * 100

        investment = BacktestInvestment(
            symbol=symbol,
            position=position,
            buy_price=buy_stock_price,
            buy_date=buy_date,
            sell_price=sell_stock_price,
            sell_date=actual_sell_date,
            profit_pct=profit_pct,
            profit=profit,
            stop_loss_price=stop_price,
        )
        return investment, uninvested

    async def invest_baseline(
        self, buy_date: datetime, sell_date: datetime, amount: float
    ) -> BacktestInvestment:
        """Invest in the baseline index using fractional shares.

        Uses the same Monday-open / Friday-close convention as `invest()` for
        apples-to-apples comparison.
        """
        buy_price_data = await datasource_service.get_index_price_at_date(
            self.db_session, self.baseline_index, buy_date.date(), nearest=True
        )
        if buy_price_data.open is None:
            raise ValueError(
                f"No open price for {self.baseline_index.value} on/near "
                f"{buy_date.date()} — cannot apply Monday-open buy convention"
            )
        baseline_index_price_buy = buy_price_data.open

        friday_sell_date = previous_friday(sell_date)
        baseline_index_price_sell = (
            await datasource_service.get_index_price_at_date(
                self.db_session,
                self.baseline_index,
                friday_sell_date.date(),
                nearest=True,
            )
        ).adj_close
        # Use fractional shares for baseline — it's a benchmark, not a real trade
        position = amount / baseline_index_price_buy
        profit = (baseline_index_price_sell - baseline_index_price_buy) * position
        profit_pct = (
            (baseline_index_price_sell - baseline_index_price_buy)
            / baseline_index_price_buy
            * 100
        )

        investment = BacktestInvestment(
            symbol=self.baseline_index.value,
            position=position,
            buy_price=baseline_index_price_buy,
            buy_date=buy_date,
            sell_price=baseline_index_price_sell,
            sell_date=friday_sell_date,
            profit_pct=profit_pct,
            profit=profit,
        )
        return investment

    async def backtest(self) -> BacktestResult:

        # Initial Setup
        balance = self.initial_balance
        baseline_balance = self.initial_balance
        backtest_rebalance: list[BacktestRebalance] = []
        date_iter = next_monday(self.date_start)  # Start from the next Monday

        while date_iter < self.date_end:
            end_date = date_iter + timedelta(weeks=self.rebalance_interval_weeks)
            # Allow partial final period — clamp to date_end
            if end_date > self.date_end:
                end_date = self.date_end

            # Skip if the (clamped) period is too short to span at least one
            # Mon-open → Fri-close holding window — previous_friday(end_date)
            # would land on or before date_iter and produce an invalid sell.
            if previous_friday(end_date) <= date_iter:
                logger.info(
                    f"Skipping final period {date_iter.date()} → {end_date.date()}: "
                    "too short for a Mon-open / Fri-close holding window"
                )
                break

            logger.info(
                f"=========== Rebalance on {date_iter.date()} (Balance: {balance}), hold til: {end_date.date()} ==========="
            )
            selected_stocks = await self.pick_stocks(date_iter)

            investments: list[BacktestInvestment] = []
            if selected_stocks:
                allocation = balance / len(selected_stocks)
                for stock in selected_stocks:
                    investment, _uninvested = await self.invest(
                        stock.symbol, date_iter, end_date, allocation
                    )
                    investments.append(investment)

            # Calculate the profit of this rebalance
            profit = sum(inv.profit for inv in investments)
            profit_pct = (profit / balance * 100) if balance > 0 else 0.0

            # Invest in the baseline index
            baseline_investment = await self.invest_baseline(
                date_iter, end_date, baseline_balance
            )

            backtest_rebalance.append(
                BacktestRebalance(
                    date=date_iter,
                    balance=balance,
                    investments=investments,
                    profit_pct=profit_pct,
                    profit=profit,
                    baseline_balance=baseline_balance,
                    baseline_profit_pct=baseline_investment.profit_pct,
                    baseline_profit=baseline_investment.profit,
                )
            )

            baseline_balance += baseline_investment.profit

            # Update the balance
            balance += profit

            # Iterate to the next rebalance date
            date_iter = end_date

        scores = compute_scores(
            backtest_rebalance=backtest_rebalance,
            rebalance_interval_weeks=self.rebalance_interval_weeks,
            initial_balance=self.initial_balance,
            final_balance=balance,
            date_start_ts=self.date_start.timestamp(),
            date_end_ts=self.date_end.timestamp(),
        )

        return BacktestResult(
            initial_balance=self.initial_balance,
            final_balance=balance,
            date_start=self.date_start,
            date_end=self.date_end,
            backtest_rebalance=backtest_rebalance,
            profit_pct=(balance - self.initial_balance) / self.initial_balance * 100,
            profit=balance - self.initial_balance,
            baseline_index=self.baseline_index,
            baseline_profit_pct=(baseline_balance - self.initial_balance)
            / self.initial_balance
            * 100,
            baseline_profit=baseline_balance - self.initial_balance,
            baseline_balance=baseline_balance,
            backtest_config=BacktestConfig(
                max_stocks=self.max_stocks,
                rebalance_interval_weeks=self.rebalance_interval_weeks,
                date_start=self.date_start,
                date_end=self.date_end,
                rule=self.rule_raw,
                ranking=self.ranking_raw,
                index=self.from_index,
                involved_keys=extract_involved_keys(self.rule_raw),
                stop_loss=self.stop_loss,
            ),
            scores=scores,
        )
