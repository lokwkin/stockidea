from datetime import datetime, timedelta
from math import floor
import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.analysis import metrics
from stockidea.datasource import constituent, market_data
from stockidea.helper import next_monday
from stockidea.rule_engine import extract_involved_keys
from stockidea.types import Investment, RebalanceHistory, SimulationConfig, SimulationResult, StockIndex, StockMetrics

logger = logging.getLogger(__name__)


class Simulator:
    db_session: AsyncSession
    initial_balance: float
    date_start: datetime
    date_end: datetime
    rebalance_interval_weeks: int
    max_stocks: int
    rule_func: Callable[[StockMetrics], bool]
    rule_raw: str

    def __init__(
        self,
        db_session: AsyncSession,
        max_stocks: int,
        rebalance_interval_weeks: int,
        date_start: datetime,
        date_end: datetime,
        rule_func: Callable[[StockMetrics], bool],
        rule_raw: str,
        from_index: StockIndex,
        baseline_index: StockIndex
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

    async def pick_stocks(self, today: datetime) -> list[StockMetrics]:
        # Get the symbols of the constituent
        symbols = await constituent.get_constituent_at(self.from_index, today.date())

        stock_metrics_batch = await metrics.get_stock_metrics_batch(
            self.db_session, symbols=symbols, metrics_date=today, back_period_weeks=52, compute_if_not_exists=True)

        filtered_stocks = metrics.apply_rule(stock_metrics_batch, rule_func=self.rule_func)

        selected_stocks = filtered_stocks[: self.max_stocks]
        logger.info(f"Selected: {[stock.symbol for stock in selected_stocks]} (from {len(filtered_stocks)} filtered)")

        return selected_stocks

    async def invest(
        self, symbol: str, buy_date: datetime, sell_date: datetime, amount: float
    ) -> Investment:
        buy_stock_price = (await market_data.get_stock_price_at_date(self.db_session, symbol, buy_date.date(), nearest=True)).adj_close
        sell_stock_price = (await market_data.get_stock_price_at_date(self.db_session, symbol, sell_date.date(), nearest=True)).adj_close
        position = floor(amount / buy_stock_price)
        profit = (sell_stock_price - buy_stock_price) * position
        profit_pct = (sell_stock_price - buy_stock_price) / buy_stock_price * 100

        investment = Investment(
            symbol=symbol,
            position=amount / buy_stock_price,
            buy_price=buy_stock_price,
            buy_date=buy_date,
            sell_price=sell_stock_price,
            sell_date=sell_date,
            profit_pct=profit_pct,
            profit=profit,
        )
        return investment

    async def invest_baseline(self, buy_date: datetime, sell_date: datetime, amount: float) -> Investment:
        baseline_index_price_buy = (await market_data.get_index_price_at_date(
            self.db_session, self.baseline_index, buy_date.date(), nearest=True)).adj_close
        baseline_index_price_sell = (await market_data.get_index_price_at_date(
            self.db_session, self.baseline_index, sell_date.date(), nearest=True)).adj_close
        position = floor(amount / baseline_index_price_buy)
        profit = (baseline_index_price_sell - baseline_index_price_buy) * position
        profit_pct = (baseline_index_price_sell - baseline_index_price_buy) / baseline_index_price_buy * 100

        investment = Investment(
            symbol=self.baseline_index.value,
            position=amount / baseline_index_price_buy,
            buy_price=baseline_index_price_buy,
            buy_date=buy_date,
            sell_price=baseline_index_price_sell,
            sell_date=sell_date,
            profit_pct=profit_pct,
            profit=profit,
        )
        return investment

    async def simulate(self) -> SimulationResult:

        # Initial Setup
        balance = self.initial_balance
        baseline_balance = self.initial_balance
        rebalance_history: list[RebalanceHistory] = []
        date_iter = next_monday(self.date_start)  # Start from the next Monday

        while date_iter < self.date_end:
            end_date = date_iter + timedelta(weeks=self.rebalance_interval_weeks)
            if end_date > self.date_end:
                break

            logger.info(
                f"=========== Rebalance on {date_iter.date()} (Balance: {balance}), hold til: {end_date.date()} ===========")
            selected_stocks = await self.pick_stocks(date_iter)

            investments: list[Investment] = []
            for stock in selected_stocks:
                # split in average
                investment = await self.invest(
                    stock.symbol, date_iter, end_date, balance / len(selected_stocks)
                )
                investments.append(investment)

            # Calculate the profit of this rebalance
            profit = sum(investment.profit for investment in investments)
            profit_pct = profit / balance

            # Invest in the baseline index
            baseline_investment = await self.invest_baseline(date_iter, end_date, balance)

            rebalance_history.append(RebalanceHistory(
                date=date_iter,
                balance=balance,
                investments=investments,
                profit_pct=profit_pct,
                profit=profit,
                baseline_balance=baseline_balance,
                baseline_profit_pct=baseline_investment.profit_pct,
                baseline_profit=baseline_investment.profit
            ))

            baseline_balance += baseline_investment.profit

            # Update the balance
            balance += profit

            # Iterate to the next rebalance date
            date_iter = end_date

        return SimulationResult(
            initial_balance=self.initial_balance,
            final_balance=balance,
            date_start=self.date_start,
            date_end=self.date_end,
            rebalance_history=rebalance_history,
            profit_pct=(balance - self.initial_balance) / self.initial_balance,
            profit=balance - self.initial_balance,
            baseline_index=self.baseline_index,
            baseline_profit_pct=(baseline_balance - self.initial_balance) / self.initial_balance,
            baseline_profit=baseline_balance - self.initial_balance,
            baseline_balance=baseline_balance,
            simulation_config=SimulationConfig(
                max_stocks=self.max_stocks,
                rebalance_interval_weeks=self.rebalance_interval_weeks,
                date_start=self.date_start,
                date_end=self.date_end,
                rule=self.rule_raw,
                index=self.from_index,
                involved_keys=extract_involved_keys(self.rule_raw)
            )
        )
