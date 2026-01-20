from dataclasses import asdict
from datetime import datetime, timedelta
import json
from math import floor
from typing import Callable

from stockpick.analysis import analysis
from stockpick import data_loader
from stockpick.config import OUTPUT_DIR
from stockpick.types import Investment, RebalanceHistory, SimulationResult, StockPrice, TrendAnalysis


class Simulator:
    initial_balance: float
    stock_prices: dict[str, list[StockPrice]] | None
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
    ):
        self.initial_balance = 10000
        self.stock_prices = None
        self.max_stocks = max_stocks
        self.rebalance_interval_weeks = rebalance_interval_weeks
        self.date_start = date_start
        self.date_end = date_end
        self.rule_func = rule_func
        self.rule_raw = rule_raw

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
        self.stock_prices = data_loader.fetch_stock_prices_batch(symbols)

        if self.stock_prices is None:
            raise ValueError("Stock prices not loaded")

        for symbol, prices in self.stock_prices.items():
            # Make sure the prices are sorted by date, from newest to oldest
            self.stock_prices[symbol].sort(key=lambda x: x.date, reverse=True)

    def pick_stocks(self, today: datetime) -> tuple[list[TrendAnalysis], str]:
        if self.stock_prices is None:
            raise ValueError("Stock prices not loaded")

        print(f"Analyzing data from {today.date()} to {today.date()}")
        analyses, filename = analysis.analyze_stock_batch(stock_prices=self.stock_prices,
                                                          analysis_date=today, back_period_weeks=52)
        filename = analysis.save_analysis(analysis=analyses, analysis_date=today)
        if filename.endswith(".json"):
            filename = filename[:-5]

        selected_stocks = analysis.apply_rule(analyses=analyses, max_stocks=self.max_stocks, rule_func=self.rule_func)
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

    def simulate(self) -> SimulationResult:
        balance = self.initial_balance
        rebalance_history: list[RebalanceHistory] = []
        date_iter = self.date_start
        while date_iter < self.date_end:
            end_date = date_iter + timedelta(weeks=self.rebalance_interval_weeks)
            if end_date > self.date_end:
                break

            print(
                f"====================== Rebalance on {date_iter.date()} (Balance: {balance})==========================")
            selected_stocks, analysis_ref = self.pick_stocks(date_iter)

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
            rule_ref=self.rule_raw,
        )


def save_simulation_result(result: SimulationResult) -> None:
    """Save simulation result to JSON file in output directory."""

    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    result_dict = asdict(result)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / "simulations" / f"simulation_{timestamp.format('%Y%m%d%H%M%S')}.json"
    output_path.write_text(json.dumps(result_dict, indent=2, default=serialize))
    print(f"✓ Simulation result saved: {output_path}")
