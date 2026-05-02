from datetime import datetime, timedelta
import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.datasource import service as datasource_service
from stockidea.helper import next_monday, previous_friday
from stockidea.rule_engine import extract_involved_keys
from stockidea.backtest.scoring import compute_scores
from stockidea.screener import service as screener_service
from stockidea.screener.types import Pick, Portfolio
from stockidea.types import (
    BacktestInvestment,
    BacktestRebalance,
    BacktestConfig,
    BacktestResult,
    SellTiming,
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
    sort_func: Callable[[StockIndicators], float] | None
    sort_raw: str
    stop_loss: StopLossConfig | None
    sell_timing: SellTiming

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
        sort_func: Callable[[StockIndicators], float],
        sort_raw: str,
        stop_loss: StopLossConfig | None = None,
        sell_timing: SellTiming = "friday_close",
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
        self.sort_func = sort_func
        self.sort_raw = sort_raw
        self.stop_loss = stop_loss
        self.sell_timing = sell_timing

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

    async def _resolve_stock_sell(
        self, symbol: str, sell_date: datetime
    ) -> tuple[datetime, float]:
        """Return (actual_sell_date, sell_price) for a stock based on sell_timing.

        - friday_close: previous_friday(sell_date) adjusted close
        - monday_open:  sell_date open (the next-rebalance Monday open)
        """
        if self.sell_timing == "friday_close":
            target = previous_friday(sell_date)
            price = (
                await datasource_service.get_stock_price_at_date(
                    self.db_session, symbol, target.date(), nearest=True
                )
            ).adj_close
            return target, price

        # monday_open
        price_data = await datasource_service.get_stock_price_at_date(
            self.db_session, symbol, sell_date.date(), nearest=True
        )
        if price_data.open is None:
            raise ValueError(
                f"No open price for {symbol} on/near {sell_date.date()} — "
                "cannot apply Monday-open sell convention"
            )
        return sell_date, price_data.open

    async def _execute_pick(
        self, pick: Pick, buy_date: datetime, sell_date: datetime
    ) -> BacktestInvestment:
        """Run the holding-period simulation for a sized pick.

        ``pick`` already carries ``buy_price``, ``target_quantity`` and
        ``stop_loss_price`` — those are computed once by the screener at the
        rebalance moment. This method handles the sell side: resolve the sell
        date/price per ``self.sell_timing``, scan for a stop-loss exit, and
        record the resulting BacktestInvestment.
        """
        buy_stock_price = pick.buy_price
        position = pick.target_quantity
        assert position is not None, (
            "screener.pick must size positions in backtest mode"
        )
        stop_price = pick.stop_loss_price

        actual_sell_date, sell_stock_price = await self._resolve_stock_sell(
            pick.symbol, sell_date
        )

        if stop_price is not None:
            exit_info = await self._find_stop_loss_exit(
                pick.symbol, buy_date, actual_sell_date, stop_price
            )
            if exit_info is not None:
                actual_sell_date, sell_stock_price = exit_info
                logger.info(
                    f"Stop loss hit for {pick.symbol}: exit {actual_sell_date.date()} "
                    f"@ {sell_stock_price:.2f} (stop={stop_price:.2f}, "
                    f"buy={buy_stock_price:.2f})"
                )

        profit = (sell_stock_price - buy_stock_price) * position
        profit_pct = (sell_stock_price - buy_stock_price) / buy_stock_price * 100

        return BacktestInvestment(
            symbol=pick.symbol,
            position=position,
            buy_price=buy_stock_price,
            buy_date=buy_date,
            sell_price=sell_stock_price,
            sell_date=actual_sell_date,
            profit_pct=profit_pct,
            profit=profit,
            stop_loss_price=stop_price,
        )

    async def _resolve_baseline_sell(
        self, sell_date: datetime
    ) -> tuple[datetime, float]:
        """Return (actual_sell_date, sell_price) for the baseline index."""
        if self.sell_timing == "friday_close":
            target = previous_friday(sell_date)
            price = (
                await datasource_service.get_index_price_at_date(
                    self.db_session, self.baseline_index, target.date(), nearest=True
                )
            ).adj_close
            return target, price

        # monday_open
        price_data = await datasource_service.get_index_price_at_date(
            self.db_session, self.baseline_index, sell_date.date(), nearest=True
        )
        if price_data.open is None:
            raise ValueError(
                f"No open price for {self.baseline_index.value} on/near "
                f"{sell_date.date()} — cannot apply Monday-open sell convention"
            )
        return sell_date, price_data.open

    async def invest_baseline(
        self, buy_date: datetime, sell_date: datetime, amount: float
    ) -> BacktestInvestment:
        """Invest in the baseline index using fractional shares.

        Uses the same buy/sell convention as `invest()` for apples-to-apples
        comparison.
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

        actual_sell_date, baseline_index_price_sell = await self._resolve_baseline_sell(
            sell_date
        )
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
            sell_date=actual_sell_date,
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

            # Skip if the (clamped) period is too short for the holding window.
            # - friday_close: needs a Friday strictly after the buy Monday
            # - monday_open:  needs end_date strictly after the buy Monday
            too_short = (
                previous_friday(end_date) <= date_iter
                if self.sell_timing == "friday_close"
                else end_date <= date_iter
            )
            if too_short:
                logger.info(
                    f"Skipping final period {date_iter.date()} → {end_date.date()}: "
                    f"too short for a Mon-open / {self.sell_timing} holding window"
                )
                break

            logger.info(
                f"=========== Rebalance on {date_iter.date()} (Balance: {balance}), hold til: {end_date.date()} ==========="
            )
            screener_result = await screener_service.pick(
                self.db_session,
                indicators_date=previous_friday(date_iter),
                buy_date=date_iter,
                rule_func=self.rule_func,
                sort_func=self.sort_func,
                max_stocks=self.max_stocks,
                from_index=self.from_index,
                stop_loss=self.stop_loss,
                # Backtester sells everything before each rebalance; pass an
                # empty-holdings portfolio so screener equally splits cash among
                # the picks (matches prior allocation = balance / len(picks)).
                portfolio=Portfolio(cash=balance, holdings=[]),
            )

            investments: list[BacktestInvestment] = []
            for pick in screener_result.picks:
                investment = await self._execute_pick(pick, date_iter, end_date)
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
                sort_expr=self.sort_raw,
                index=self.from_index,
                involved_keys=extract_involved_keys(self.rule_raw),
                stop_loss=self.stop_loss,
                sell_timing=self.sell_timing,
            ),
            scores=scores,
        )
