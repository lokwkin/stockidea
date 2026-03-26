

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
    # Slope — linear trend strength (% of starting price per week)
    slope_pct_13w: float
    slope_pct_26w: float
    slope_pct_52w: float
    # R² — regression fit quality (0–1)
    r_squared_13w: float
    r_squared_26w: float
    r_squared_52w: float
    # Log trend
    log_slope_13w: float
    log_r_squared_13w: float
    log_slope_26w: float
    log_r_squared_26w: float
    log_slope_52w: float
    log_r_squared_52w: float
    # Point-to-point change
    change_pct_1w: float
    change_pct_2w: float
    change_pct_4w: float
    change_pct_13w: float
    change_pct_26w: float
    change_pct_52w: float
    # Max single-period swing
    max_jump_pct_1w: float
    max_drop_pct_1w: float
    max_jump_pct_2w: float
    max_drop_pct_2w: float
    max_jump_pct_4w: float
    max_drop_pct_4w: float
    # Max drawdown (peak-to-trough, positive value)
    max_drawdown_pct_4w: float
    max_drawdown_pct_13w: float
    max_drawdown_pct_26w: float
    max_drawdown_pct_52w: float
    # Fraction of up-weeks (0.0–1.0)
    pct_weeks_positive_4w: float
    pct_weeks_positive_13w: float
    pct_weeks_positive_26w: float
    pct_weeks_positive_52w: float

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


# =============================================================================
# Job Queue Models
# =============================================================================

import uuid as _uuid


class SimulationJob(BaseModel):
    id: _uuid.UUID
    status: str  # pending | running | completed | failed
    simulation_id: _uuid.UUID | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EnqueuedJob(BaseModel):
    job_id: _uuid.UUID
    status: str
