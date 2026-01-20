

from dataclasses import dataclass
from datetime import datetime, date


@dataclass
class StockPrice:
    """Represents a single day's stock price data."""

    symbol: str
    date: date
    price: float
    volume: int


@dataclass
class TrendAnalysis:
    """Analysis results for a stock between two dates."""

    symbol: str
    weeks_above_1_week_ago: int
    weeks_above_2_weeks_ago: int
    weeks_above_4_weeks_ago: int
    biggest_weekly_jump_pct: float
    biggest_weekly_drop_pct: float
    biggest_biweekly_jump_pct: float
    biggest_biweekly_drop_pct: float
    biggest_monthly_jump_pct: float
    biggest_monthly_drop_pct: float
    change_1y_pct: float
    change_6m_pct: float  # 6 month change
    change_3m_pct: float  # 3 month change
    change_1m_pct: float  # 1 month change
    total_weeks: int
    # Trend analysis (linear regression)
    trend_slope_pct: float  # Weekly slope as % of starting price
    trend_r_squared: float  # R² (0-1), how well data fits the trend line

    def __str__(self) -> str:
        return (
            f"Analysis for {self.symbol} ({self.total_weeks} weeks)\n"
            f"{'─' * 50}\n"
            f"Weeks closing > 1 week ago:  {self.weeks_above_1_week_ago:3d} ({self.weeks_above_1_week_ago / max(1, self.total_weeks - 1) * 100:5.1f}%)\n"
            f"Weeks closing > 2 weeks ago: {self.weeks_above_2_weeks_ago:3d} ({self.weeks_above_2_weeks_ago / max(1, self.total_weeks - 2) * 100:5.1f}%)\n"
            f"Weeks closing > 4 weeks ago: {self.weeks_above_4_weeks_ago:3d} ({self.weeks_above_4_weeks_ago / max(1, self.total_weeks - 4) * 100:5.1f}%)\n"
            f"{'─' * 50}\n"
            f"Biggest weekly jump:    {self.biggest_weekly_jump_pct:+7.2f}%\n"
            f"Biggest weekly drop:    {self.biggest_weekly_drop_pct:+7.2f}%\n"
            f"Biggest biweekly jump:  {self.biggest_biweekly_jump_pct:+7.2f}%\n"
            f"Biggest biweekly drop:  {self.biggest_biweekly_drop_pct:+7.2f}%\n"
            f"Biggest monthly jump:   {self.biggest_monthly_jump_pct:+7.2f}%\n"
            f"Biggest monthly drop:   {self.biggest_monthly_drop_pct:+7.2f}%\n"
            f"{'─' * 50}\n"
            f"Trend slope (per week): {self.trend_slope_pct:+7.3f}%\n"
            f"Trend stability (R²):   {self.trend_r_squared:7.3f}\n"
            f"{'─' * 50}\n"
            f"Change (1 month):   {self.change_1m_pct:+7.2f}%\n"
            f"Change (3 months):  {self.change_3m_pct:+7.2f}%\n"
            f"Change (6 months):  {self.change_6m_pct:+7.2f}%\n"
            f"Change (1 year):    {self.change_1y_pct:+7.2f}%"
        )


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
    rule_ref: str | None = None
