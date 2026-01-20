from dataclasses import dataclass
import inspect
from datetime import datetime, timedelta
from math import floor
from typing import Callable

from stockpick.analysis.analysis import save_analysis
from stockpick.analysis.price_analyzer import PriceAnalysis, analyze_stock_batch
from stockpick.fetch_prices import StockPrice, fetch_stock_prices_batch


@dataclass
class Investment:
    symbol: str
    position: float
    buy_price: float
    buy_date: datetime
    sell_price: float
    sell_date: datetime
    profit_pct: float
    profit: float


@dataclass
class RebalanceHistory:
    date: datetime
    balance: float
    analysis_ref: str
    investments: list[Investment]
    profit_pct: float
    profit: float


@dataclass
class SimulationResult:
    initial_balance: float
    date_start: datetime
    date_end: datetime
    rebalance_history: list[RebalanceHistory]
    profit_pct: float
    profit: float
    rule_ref: str


class Simulator:
    initial_balance: float
    stock_prices: dict[str, list[StockPrice]] | None
    date_start: datetime
    date_end: datetime
    rebalance_interval_weeks: int
    max_stocks: int

    def __init__(
        self,
        max_stocks: int,
        rebalance_interval_weeks: int,
        date_start: datetime,
        date_end: datetime,
    ):
        self.initial_balance = 10000
        self.stock_prices = None
        self.max_stocks = max_stocks
        self.rebalance_interval_weeks = rebalance_interval_weeks
        self.date_start = date_start
        self.date_end = date_end

    def get_stock_price(self, symbol: str, date: datetime) -> StockPrice:
        if self.stock_prices is None or symbol not in self.stock_prices:
            raise ValueError(f"Stock prices not loaded for symbol: {symbol}")

        price = next(
            (price for price in self.stock_prices[symbol] if price.date == date.date()), None
        )
        if price is not None:
            return price

        # stock_prices[symbol] is sorted by date, from newest to oldest
        price = next((price for price in self.stock_prices[symbol] if price.date < date.date()), None)
        if price is not None:
            print(f"Using the nearest price before the date: {date.date()} --> {price.date}")
            return price

        raise ValueError(
            f"Stock price not found for symbol: {symbol} on date: {date.date()}"
        )

    def load_stock_prices(self, symbols: list[str]) -> None:
        self.stock_prices = fetch_stock_prices_batch(symbols)

        for symbol, prices in self.stock_prices.items():
            # Make sure the prices are sorted by date, from newest to oldest
            self.stock_prices[symbol].sort(key=lambda x: x.date, reverse=True)

    def pick_stocks(
        self, today: datetime, criteria: Callable[[PriceAnalysis], bool]
    ) -> tuple[list[PriceAnalysis], str]:
        if self.stock_prices is None:
            raise ValueError("Stock prices not loaded")

        filtered_stocks: list[PriceAnalysis] = []
        analyze_from = today - timedelta(weeks=52 * 1)
        print(f"Analyzing data from {analyze_from.date()} to {today.date()}")
        analyses = analyze_stock_batch(stock_prices=self.stock_prices,
                                       from_date=analyze_from.date(), to_date=today.date())
        filename = save_analysis(analysis=analyses, analysis_date=today)
        if filename.endswith(".json"):
            filename = filename[:-5]

        # Filter stocks by criteria
        filtered_stocks = [analysis for analysis in analyses if criteria(analysis)]

        # Sort by weight
        # TODO: use a more sophisticated algorithm
        filtered_stocks.sort(key=lambda x: x.trend_slope_pct, reverse=True)
        selected_stocks = filtered_stocks[: self.max_stocks]
        print(f"Selected: {[stock.symbol for stock in selected_stocks]} (from {len(filtered_stocks)} filtered)")
        return selected_stocks, filename

    def invest(
        self, symbol: str, buy_date: datetime, sell_date: datetime, amount: float
    ) -> Investment:
        buy_stock_price = self.get_stock_price(symbol, buy_date).price
        sell_stock_price = self.get_stock_price(symbol, sell_date).price
        position = floor(amount / buy_stock_price)
        profit = (sell_stock_price - buy_stock_price) * position
        profit_pct = profit / buy_stock_price

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

    def simulate(
        self, criteria: Callable[[PriceAnalysis], bool]
    ) -> SimulationResult:
        balance = self.initial_balance
        rebalance_history: list[RebalanceHistory] = []
        date_iter = self.date_start
        while date_iter < self.date_end:
            end_date = date_iter + timedelta(weeks=self.rebalance_interval_weeks)
            if end_date > self.date_end:
                break

            print(
                f"====================== Rebalance on {date_iter.date()} (Balance: {balance})==========================")
            selected_stocks, analysis_ref = self.pick_stocks(date_iter, criteria)

            investments: list[Investment] = []
            for stock in selected_stocks:
                # split in average
                investment = self.invest(
                    stock.symbol, date_iter, end_date, balance / len(selected_stocks)
                )
                investments.append(investment)

            # Calculate the profit of this rebalance
            profit = sum(investment.profit for investment in investments)
            profit_pct = profit / balance

            rebalance_history.append(RebalanceHistory(date=date_iter, balance=balance,
                                     analysis_ref=analysis_ref, investments=investments, profit_pct=profit_pct, profit=profit))

            # Update the balance
            balance += profit

            # Iterate to the next rebalance date
            date_iter = end_date

        return SimulationResult(
            initial_balance=self.initial_balance,
            date_start=self.date_start,
            date_end=self.date_end,
            rebalance_history=rebalance_history,
            profit_pct=(balance - self.initial_balance) / self.initial_balance,
            profit=balance - self.initial_balance,
            rule_ref=inspect.getsource(criteria),
        )
