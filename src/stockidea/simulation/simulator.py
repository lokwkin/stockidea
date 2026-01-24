from datetime import datetime, timedelta
from math import floor
import logging
from typing import Callable
from uuid import UUID

from stockidea.analysis import analysis
from stockidea.datasource import constituent, market_data
from stockidea.datasource.database import conn
from stockidea.datasource.database.queries import save_simulation_result as save_simulation_to_db
from stockidea.helper import next_monday
from stockidea.types import Investment, RebalanceHistory, SimulationConfig, SimulationResult, StockIndex, TrendAnalysis

logger = logging.getLogger(__name__)


class Simulator:
    initial_balance: float
    date_start: datetime
    date_end: datetime
    rebalance_interval_weeks: int
    max_stocks: int
    rule_func: Callable[[TrendAnalysis], bool]
    rule_raw: str

    def __init__(
        self,
        max_stocks: int,
        rebalance_interval_weeks: int,
        date_start: datetime,
        date_end: datetime,
        rule_func: Callable[[TrendAnalysis], bool],
        rule_raw: str,
        from_index: StockIndex,
        baseline_index: StockIndex
    ):
        self.initial_balance = 10000
        self.max_stocks = max_stocks
        self.rebalance_interval_weeks = rebalance_interval_weeks
        self.date_start = date_start
        self.date_end = date_end
        self.rule_func = rule_func
        self.rule_raw = rule_raw
        self.from_index = from_index
        self.baseline_index = baseline_index

    async def pick_stocks(self, today: datetime) -> tuple[list[TrendAnalysis], str]:
        # Get the symbols of the constituent
        symbols = await constituent.get_constituent_at(self.from_index, today.date())

        # Get the stock price histories
        stock_prices = await market_data.get_stock_price_batch_histories(
            symbols, from_date=today.date() - timedelta(weeks=52), to_date=today.date())

        result = analysis.load_analysis(today)
        if result is not None:
            # Got the analysis from the cache
            analyses, filename = result
        else:
            # No analysis found in the cache, analyze the data
            logger.info(f"Analyzing data from {today.date()} to {today.date()}")

            analyses, filename = analysis.analyze_stock_batch(stock_prices=stock_prices,
                                                              analysis_date=today, back_period_weeks=52)

        if filename.endswith(".json"):
            filename = filename[:-5]

        selected_stocks = analysis.apply_rule(analyses=analyses, max_stocks=self.max_stocks, rule_func=self.rule_func)
        return selected_stocks, filename

    async def invest(
        self, symbol: str, buy_date: datetime, sell_date: datetime, amount: float
    ) -> Investment:
        buy_stock_price = (await market_data.get_stock_price_at_date(symbol, buy_date.date(), nearest=True)).adj_close
        sell_stock_price = (await market_data.get_stock_price_at_date(symbol, sell_date.date(), nearest=True)).adj_close
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
            self.baseline_index, buy_date.date(), nearest=True)).adj_close
        baseline_index_price_sell = (await market_data.get_index_price_at_date(
            self.baseline_index, sell_date.date(), nearest=True)).adj_close
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
                f"====================== Rebalance on {date_iter.date()} (Balance: {balance})==========================")
            selected_stocks, analysis_ref = await self.pick_stocks(date_iter)

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
                analysis_ref=analysis_ref,
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
                index=self.from_index
            )
        )


async def save_simulation_result(result: SimulationResult) -> UUID:
    """
    Save simulation result to database.
    Returns the simulation ID.
    """
    async with conn.get_db_session() as db_session:
        simulation_id = await save_simulation_to_db(db_session, result)
        return simulation_id
