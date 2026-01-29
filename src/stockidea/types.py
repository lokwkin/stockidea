

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


# =============================================================================
# Stock Metrics Model
# =============================================================================
class StockMetrics(BaseModel):
    symbol: str
    date: date
    total_weeks: int
    # Trend metrics (regression-based)
    linear_slope_pct: float
    linear_r_squared: float
    log_slope: float
    log_r_squared: float
    # Return metrics (point-to-point changes)
    change_1w_pct: float
    change_2w_pct: float
    change_1m_pct: float
    change_3m_pct: float
    change_6m_pct: float
    change_1y_pct: float
    # Volatility metrics (max swings)
    max_jump_1w_pct: float
    max_drop_1w_pct: float
    max_jump_2w_pct: float
    max_drop_2w_pct: float
    max_jump_4w_pct: float
    max_drop_4w_pct: float

# =============================================================================
# Simulation Models
# =============================================================================


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
