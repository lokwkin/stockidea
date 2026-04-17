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
    volume: int | None = None


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
    # Linear regression slope (% of starting price per week) per window
    slope_pct_13w: float
    slope_pct_26w: float
    slope_pct_52w: float
    # Linear regression R² per window
    r_squared_4w: float
    r_squared_13w: float
    r_squared_26w: float
    r_squared_52w: float
    # Log regression slope and R² per window
    log_slope_13w: float
    log_r_squared_13w: float
    log_slope_26w: float
    log_r_squared_26w: float
    log_slope_52w: float
    log_r_squared_52w: float
    # Point-to-point percentage change per window
    change_pct_1w: float
    change_pct_2w: float
    change_pct_4w: float
    change_pct_13w: float
    change_pct_26w: float
    change_pct_52w: float
    # Max single-period jump / drop (%)
    max_jump_pct_1w: float
    max_drop_pct_1w: float
    max_jump_pct_2w: float
    max_drop_pct_2w: float
    max_jump_pct_4w: float
    max_drop_pct_4w: float
    # Weekly return std-dev (full series, 52w)
    return_std_52w: float
    downside_std_52w: float
    # Max peak-to-trough drawdown (positive %) per window
    max_drawdown_pct_4w: float
    max_drawdown_pct_13w: float
    max_drawdown_pct_26w: float
    max_drawdown_pct_52w: float
    # Fraction of up-weeks (0.0–1.0) per window
    pct_weeks_positive_4w: float
    pct_weeks_positive_13w: float
    pct_weeks_positive_26w: float
    pct_weeks_positive_52w: float
    # Momentum shape
    acceleration_pct_13w: (
        float  # recent-half slope minus earlier-half slope over 13w (% per week)
    )
    from_high_pct_4w: float  # distance from 4-week high (always <= 0)


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
    ranking: str = "change_pct_13w / return_std_52w"
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
    ranking: str | None = None
    profit_pct: float
    baseline_profit_pct: float
    max_stocks: int
    rebalance_interval_weeks: int
    index: str
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
    created_at: datetime
    updated_at: datetime
    messages: list[StrategyMessage] = []
    backtests: list[StrategyBacktestSummary] = []
    llm_history_json: str | None = None
