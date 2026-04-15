from datetime import datetime, timedelta
from math import floor
import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.indicators import service as indicators_service
from stockidea.datasource import service as datasource_service
from stockidea.helper import next_monday
from stockidea.rule_engine import extract_involved_keys
from stockidea.backtest.scoring import compute_scores
from stockidea.types import (
    BacktestInvestment,
    BacktestRebalance,
    BacktestConfig,
    BacktestResult,
    StockIndex,
    StockIndicators,
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

    async def pick_stocks(self, today: datetime) -> list[StockIndicators]:
        # Get the symbols of the constituent
        symbols = await datasource_service.get_constituent_at(
            self.db_session, self.from_index, today.date()
        )

        stock_indicators_batch = await indicators_service.get_stock_indicators_batch(
            self.db_session,
            symbols=symbols,
            indicators_date=today,
            back_period_weeks=52,
            compute_if_not_exists=True,
        )

        filtered_stocks = indicators_service.apply_rule(
            stock_indicators_batch, rule_func=self.rule_func
        )

        selected_stocks = filtered_stocks[: self.max_stocks]
        logger.info(
            f"Selected: {[stock.symbol for stock in selected_stocks]} (from {len(filtered_stocks)} filtered)"
        )

        return selected_stocks

    async def invest(
        self, symbol: str, buy_date: datetime, sell_date: datetime, amount: float
    ) -> tuple[BacktestInvestment, float]:
        """Invest in a stock. Returns (investment, uninvested_cash)."""
        buy_stock_price = (
            await datasource_service.get_stock_price_at_date(
                self.db_session, symbol, buy_date.date(), nearest=True
            )
        ).adj_close
        sell_stock_price = (
            await datasource_service.get_stock_price_at_date(
                self.db_session, symbol, sell_date.date(), nearest=True
            )
        ).adj_close
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
            sell_date=sell_date,
            profit_pct=profit_pct,
            profit=profit,
        )
        return investment, uninvested

    async def invest_baseline(
        self, buy_date: datetime, sell_date: datetime, amount: float
    ) -> BacktestInvestment:
        """Invest in the baseline index using fractional shares (benchmark, not real trade)."""
        baseline_index_price_buy = (
            await datasource_service.get_index_price_at_date(
                self.db_session, self.baseline_index, buy_date.date(), nearest=True
            )
        ).adj_close
        baseline_index_price_sell = (
            await datasource_service.get_index_price_at_date(
                self.db_session, self.baseline_index, sell_date.date(), nearest=True
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
            sell_date=sell_date,
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
                index=self.from_index,
                involved_keys=extract_involved_keys(self.rule_raw),
            ),
            scores=scores,
        )
