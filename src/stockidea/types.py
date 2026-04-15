from datetime import datetime, date
import enum
import uuid as _uuid

from pydantic import BaseModel


class StockIndex(enum.Enum):
    SP500 = "SP500"
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
# Stock Indicators Model
# =============================================================================
class StockIndicators(BaseModel):
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
    change_4w_pct: float
    change_13w_pct: float
    change_26w_pct: float
    change_1y_pct: float
    # Volatility metrics (max swings)
    max_jump_1w_pct: float
    max_drop_1w_pct: float
    max_jump_2w_pct: float
    max_drop_2w_pct: float
    max_jump_4w_pct: float
    max_drop_4w_pct: float
    # Volatility metrics (statistical)
    weekly_return_std: float  # std dev of weekly % returns
    downside_std: float  # std dev of negative weekly returns only
    # Stability metrics
    max_drawdown_pct: float  # positive value: e.g. 18.5 means fell 18.5% from peak
    pct_weeks_positive: float  # 0.0–1.0 fraction of up-weeks
    slope_13w_pct: float  # linear slope over last 13 weeks (% per week)
    r_squared_13w: float  # R² of 13-week regression
    r_squared_4w: float  # R² of 4-week regression (short-term trend consistency)
    slope_26w_pct: float  # linear slope over last 26 weeks (% per week)
    r_squared_26w: float  # R² of 26-week regression
    # Momentum shape
    acceleration_13w: float  # recent-half slope minus earlier-half slope over 13w
    pct_from_4w_high: float  # distance from 4-week high (always <= 0)


# =============================================================================
# Backtest Models
# =============================================================================


class BacktestInvestment(BaseModel):
    symbol: str
    position: float
    buy_price: float
    buy_date: datetime
    sell_price: float
    sell_date: datetime
    profit_pct: float
    profit: float


class BacktestRebalance(BaseModel):
    date: datetime
    balance: float
    investments: list[BacktestInvestment]
    profit_pct: float
    profit: float

    baseline_profit_pct: float
    baseline_profit: float
    baseline_balance: float


class BacktestScores(BaseModel):
    """Objective scores computed from backtest results."""

    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_weeks: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    total_rebalances: int


class BacktestConfig(BaseModel):
    max_stocks: int
    rebalance_interval_weeks: int
    date_start: datetime
    date_end: datetime
    rule: str
    index: StockIndex
    involved_keys: list[str] = []


class BacktestResult(BaseModel):
    initial_balance: float
    final_balance: float
    date_start: datetime
    date_end: datetime
    backtest_rebalance: list[BacktestRebalance]
    profit_pct: float
    profit: float
    baseline_index: StockIndex
    baseline_profit_pct: float
    baseline_profit: float
    baseline_balance: float
    backtest_config: BacktestConfig
    scores: BacktestScores | None = None


# =============================================================================
# Job Queue Models
# =============================================================================


class BacktestJob(BaseModel):
    id: _uuid.UUID
    status: str  # pending | running | completed | failed
    backtest_id: _uuid.UUID | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EnqueuedJob(BaseModel):
    job_id: _uuid.UUID
    status: str


# =============================================================================
# Strategy Models
# =============================================================================


class StrategyCreate(BaseModel):
    instruction: str
    model: str = "claude-sonnet-4-20250514"
    date_start: date | None = None
    date_end: date | None = None


class StrategyMessage(BaseModel):
    id: _uuid.UUID
    role: str  # "user" | "assistant"
    content_json: str  # JSON string
    created_at: datetime
    sequence: int


class StrategySummary(BaseModel):
    id: _uuid.UUID
    name: str
    instruction: str
    model: str
    status: str
    created_at: datetime
    updated_at: datetime


class StrategyBacktestSummary(BaseModel):
    id: _uuid.UUID
    rule: str
    profit_pct: float
    baseline_profit_pct: float
    scores: BacktestScores | None = None
    created_at: datetime


class StrategyDetail(BaseModel):
    id: _uuid.UUID
    name: str
    instruction: str
    model: str
    date_start: date
    date_end: date
    status: str
    final_rule: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[StrategyMessage] = []
    backtests: list[StrategyBacktestSummary] = []
    llm_history_json: str | None = None
