from datetime import datetime, date
import enum
from typing import Literal
import uuid as _uuid

from pydantic import BaseModel, model_validator


class StockIndex(enum.Enum):
    SP500 = "SP500"
    NASDAQ = "NASDAQ"


class FMPAdjustedStockPrice(BaseModel):
    symbol: str
    date: str
    adjOpen: float
    adjHigh: float
    adjLow: float
    adjClose: float
    volume: int


class FMPFullPrice(BaseModel):
    """Unadjusted OHLCV from FMP /historical-price-eod/full (works for indices)."""

    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockPrice(BaseModel):
    """Represents a single day's stock price data."""

    symbol: str
    date: date
    adj_close: float
    open: float | None = None
    low: float | None = None
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
    # Moving average structure (price relative to SMA, %)
    price_vs_ma20_pct: float = 0.0
    price_vs_ma50_pct: float = 0.0
    price_vs_ma100_pct: float = 0.0
    price_vs_ma200_pct: float = 0.0
    ma50_vs_ma200_pct: float = 0.0


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
    stop_loss_price: float | None = None


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


# When the holding period closes:
# - "friday_close":  sell at previous_friday(end_date) adjusted close (current default;
#                    weekend gap before the next Monday-open buy)
# - "monday_open":   sell at end_date open — the next rebalance Monday's open price
#                    (no weekend gap; flat continuous capital across rebalances)
SellTiming = Literal["friday_close", "monday_open"]


# SMA periods exposed to stop-loss expressions as ``sma_20``, ``sma_50`` etc.
STOP_LOSS_EXPR_SMA_PERIODS = (20, 50, 100, 200)


class StopLossConfig(BaseModel):
    """Per-position stop loss configuration.

    Stop level is **static at buy time** — computed once when the position is
    opened and held fixed for the entire holding period.

    The stop price is computed by evaluating ``expression`` against a context
    containing ``buy_price`` (Monday-open fill price) and ``sma_{20,50,100,200}``
    (the prior trading day's SMA — never lookahead). Examples:

      ``buy_price * 0.95``      # 5% below buy price
      ``sma_50 * 0.95``         # 95% of SMA50 at buy time
      ``sma_200``               # at SMA200 at buy time

    A computed stop ``>= buy_price`` is rejected (treated as "no stop loss" for
    that position) since an above-buy stop would fire immediately on day 1.
    """

    expression: str

    @model_validator(mode="after")
    def _validate(self) -> "StopLossConfig":
        if not self.expression.strip():
            raise ValueError("stop_loss.expression must not be empty")
        return self


class BacktestConfig(BaseModel):
    max_stocks: int
    rebalance_interval_weeks: int
    date_start: datetime
    date_end: datetime
    rule: str
    sort_expr: str = "change_pct_13w / return_std_52w"
    index: StockIndex
    involved_keys: list[str] = []
    stop_loss: StopLossConfig | None = None
    sell_timing: SellTiming = "friday_close"
    # Per-fill slippage friction (% of price). Applied symmetrically: buys fill
    # above the open, period-end sells below the close, stop-loss exits below
    # the stop trigger. Same friction is applied to the baseline for
    # apples-to-apples comparison. Default 0.2%.
    slippage_pct: float = 0.2


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
    sort_expr: str | None = None
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
