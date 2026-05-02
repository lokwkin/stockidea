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


SUPPORTED_STOP_LOSS_MA_PERIODS = (20, 50, 100, 200)


# When the holding period closes:
# - "friday_close":  sell at previous_friday(end_date) adjusted close (current default;
#                    weekend gap before the next Monday-open buy)
# - "monday_open":   sell at end_date open — the next rebalance Monday's open price
#                    (no weekend gap; flat continuous capital across rebalances)
SellTiming = Literal["friday_close", "monday_open"]


class StopLossConfig(BaseModel):
    """Per-position stop loss configuration.

    Stop level is **static at buy time** — computed once when the position is
    opened and held fixed for the entire holding period.

    Note: An alternative would be a *trailing/rolling* stop where the MA is
    recomputed every day during the hold so the stop level moves with the MA
    (acts like a trailing MA stop). Not implemented here.
    """

    type: Literal["percent", "ma_percent"]
    # percent:    % below buy price (e.g. 5 ⇒ stop = buy_price * 0.95).
    # ma_percent: % of MA at buy time (e.g. 95 ⇒ stop = 0.95 * MA{n}_at_buy).
    value: float
    # Required for type=="ma_percent"; one of SUPPORTED_STOP_LOSS_MA_PERIODS.
    ma_period: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> "StopLossConfig":
        if self.value <= 0:
            raise ValueError("stop_loss.value must be > 0")
        if self.type == "ma_percent":
            if self.ma_period is None:
                raise ValueError(
                    "stop_loss.ma_period is required when type='ma_percent'"
                )
            if self.ma_period not in SUPPORTED_STOP_LOSS_MA_PERIODS:
                raise ValueError(
                    f"stop_loss.ma_period must be one of {SUPPORTED_STOP_LOSS_MA_PERIODS}"
                )
        else:
            if self.ma_period is not None:
                raise ValueError(
                    "stop_loss.ma_period only allowed when type='ma_percent'"
                )
        return self

    @classmethod
    def parse_options(
        cls, *, pct: float | None = None, ma_spec: str | None = None
    ) -> "StopLossConfig | None":
        """Build a StopLossConfig from CLI / env style options.

        ``pct``  : stop loss as % below buy price (e.g. ``5`` ⇒ 95% of buy).
        ``ma_spec`` : ``"PERIOD:PERCENT"`` (e.g. ``"50:95"`` ⇒ 95% of SMA50_at_buy).
        Returns None when both are None. Raises ValueError on conflict / bad format.
        """
        if pct is not None and ma_spec is not None:
            raise ValueError(
                "stop-loss pct and stop-loss ma options are mutually exclusive"
            )
        if pct is not None:
            return cls(type="percent", value=pct)
        if ma_spec is not None:
            try:
                period_str, pct_str = ma_spec.split(":", 1)
                return cls(
                    type="ma_percent",
                    ma_period=int(period_str),
                    value=float(pct_str),
                )
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Invalid stop-loss ma spec '{ma_spec}' "
                    f"(expected 'PERIOD:PERCENT'): {exc}"
                )
        return None


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
