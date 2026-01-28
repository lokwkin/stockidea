

from datetime import datetime, date
import enum

from pydantic import BaseModel


class StockIndex(enum.Enum):
    SP500 = "SP500"
    DOWJONES = "DOWJONES"
    NASDAQ = "NASDAQ"


class FMPLightPrice(BaseModel):
    symbol: str
    date: str
    price: float
    volume: int


class FMPAdjustedStockPrice(BaseModel):
    symbol: str
    date: str
    adjOpen: float
    adjHigh: float
    adjLow: float
    adjClose: float
    volume: int


class StockPrice(BaseModel):
    """Represents a single day's stock price data."""

    symbol: str
    date: date
    adj_close: float


class ConstituentChange(BaseModel):
    date: date
    added_symbol: str | None = None
    removed_symbol: str | None = None


class TrendAnalysis(BaseModel):
    """Analysis results for a stock between two dates."""

    symbol: str
    max_jump_1w_pct: float
    max_drop_1w_pct: float
    max_jump_2w_pct: float
    max_drop_2w_pct: float
    max_jump_4w_pct: float
    max_drop_4w_pct: float
    change_1y_pct: float
    change_6m_pct: float  # 6 month change
    change_3m_pct: float  # 3 month change
    change_1m_pct: float  # 1 month change
    change_2w_pct: float  # 2 week change
    change_1w_pct: float  # 1 week change
    total_weeks: int
    linear_slope_pct: float  # Linear slope as % of starting price
    linear_r_squared: float  # Linear R² (0-1), how well data fits the trend line
    log_slope: float  # Log slope as % of starting price
    log_r_squared: float  # Log R² (0-1), how well data fits the trend line

    def __str__(self) -> str:
        return (
            f"Analysis for {self.symbol} ({self.total_weeks} weeks)\n"
            f"{'─' * 50}\n"
            f"Max weekly jump:    {self.max_jump_1w_pct:+7.2f}%\n"
            f"Max weekly drop:    {self.max_drop_1w_pct:+7.2f}%\n"
            f"Max biweekly jump:  {self.max_jump_2w_pct:+7.2f}%\n"
            f"Max biweekly drop:  {self.max_drop_2w_pct:+7.2f}%\n"
            f"Max monthly jump:   {self.max_jump_4w_pct:+7.2f}%\n"
            f"Max monthly drop:   {self.max_drop_4w_pct:+7.2f}%\n"
            f"{'─' * 50}\n"
            f"Linear trend slope (per week): {self.linear_slope_pct:7.3f}\n"
            f"Linear trend stability (R²):   {self.linear_r_squared:7.3f}\n"
            f"Log trend slope (per year): {self.log_slope:+7.3f}%\n"
            f"Log trend stability (R²):   {self.log_r_squared:7.3f}\n"
            f"{'─' * 50}\n"
            f"Change (1 week):    {self.change_1w_pct:+7.2f}%\n"
            f"Change (2 weeks):   {self.change_2w_pct:+7.2f}%\n"
            f"Change (1 month):   {self.change_1m_pct:+7.2f}%\n"
            f"Change (3 months):  {self.change_3m_pct:+7.2f}%\n"
            f"Change (6 months):  {self.change_6m_pct:+7.2f}%\n"
            f"Change (1 year):    {self.change_1y_pct:+7.2f}%"
        )


class Investment(BaseModel):
    symbol: str
    position: float
    buy_price: float
    buy_date: datetime
    sell_price: float
    sell_date: datetime
    profit_pct: float
    profit: float


class RebalanceHistory(BaseModel):
    date: datetime
    balance: float
    analysis_ref: str
    investments: list[Investment]
    profit_pct: float
    profit: float

    baseline_profit_pct: float
    baseline_profit: float
    baseline_balance: float


class SimulationConfig(BaseModel):
    max_stocks: int
    rebalance_interval_weeks: int
    date_start: datetime
    date_end: datetime
    rule: str
    index: StockIndex
    involved_keys: list[str] = []


class SimulationResult(BaseModel):
    initial_balance: float
    final_balance: float
    date_start: datetime
    date_end: datetime
    rebalance_history: list[RebalanceHistory]
    profit_pct: float
    profit: float
    baseline_index: StockIndex
    baseline_profit_pct: float
    baseline_profit: float
    baseline_balance: float
    simulation_config: SimulationConfig
