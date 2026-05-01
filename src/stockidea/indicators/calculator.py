from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import Callable

import numpy as np
from scipy import stats  # type: ignore

from stockidea.types import StockIndicators, StockPrice

logger = logging.getLogger(__name__)


@dataclass
class WeeklyData:
    """Represents one week's stock data."""

    week_ending: date
    closing_price: float


def _get_week_ending(d: date) -> date:
    """Get the Friday of the week for a given date."""
    days_until_friday = (4 - d.weekday()) % 7
    if days_until_friday == 0 and d.weekday() != 4:
        days_until_friday = 7
    return d + timedelta(days=days_until_friday) if d.weekday() != 4 else d


def _aggregate_to_weekly(
    prices: list[StockPrice], date_from: date, date_to: date
) -> list[WeeklyData]:
    """
    Aggregate daily prices into weekly data points.

    Uses Friday's closing price as the weekly close.
    If Friday data is missing, uses the last available day of that week.
    """
    filtered = [p for p in prices if p.date >= date_from and p.date <= date_to]
    filtered.sort(key=lambda x: x.date)

    if not filtered:
        return []

    weeks: dict[date, list[StockPrice]] = {}
    for price in filtered:
        week_end = _get_week_ending(price.date)
        if week_end not in weeks:
            weeks[week_end] = []
        weeks[week_end].append(price)

    weekly_data = []
    for week_end, week_prices in sorted(weeks.items()):
        last_day = max(week_prices, key=lambda x: x.date)
        weekly_data.append(
            WeeklyData(week_ending=week_end, closing_price=last_day.adj_close)
        )

    return weekly_data


def _calculate_pct_change(old: float, new: float) -> float:
    """Percentage change from old to new value."""
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100


def _pt_change(weekly_data: list[WeeklyData], n: int) -> float:
    """Point-to-point % change over the last n weeks."""
    n = min(n, len(weekly_data) - 1)
    if n <= 0:
        return 0.0
    return _calculate_pct_change(
        weekly_data[-n - 1].closing_price, weekly_data[-1].closing_price
    )


def _linregress_slope_pct_r2(window: list[WeeklyData]) -> tuple[float, float]:
    """Linear regression slope (% of window starting price per week) and R²."""
    if len(window) < 3:
        return 0.0, 0.0
    x = np.arange(len(window))
    y = np.array([w.closing_price for w in window])
    slope, _, r_value, _, _ = stats.linregress(x, y)
    base = window[0].closing_price
    slope_pct = float((slope / base) * 100) if base != 0 else 0.0
    return slope_pct, float(r_value**2)


def _log_slope_r2(window: list[WeeklyData]) -> tuple[float, float]:
    """Log-price linear regression slope and R²."""
    if len(window) < 3:
        return 0.0, 0.0
    x = np.arange(len(window))
    y = np.log(np.array([w.closing_price for w in window]))
    slope, _, r_value, _, _ = stats.linregress(x, y)
    return float(slope), float(r_value**2)


def _max_drawdown_pct(prices: np.ndarray) -> float:
    """Max peak-to-trough decline as a positive percentage."""
    if len(prices) < 2:
        return 0.0
    peak = np.maximum.accumulate(prices)
    drawdowns = (prices - peak) / peak * 100
    return float(-np.min(drawdowns))


def _pct_positive(changes: list[float]) -> float:
    """Fraction of values greater than zero."""
    return sum(1 for c in changes if c > 0) / len(changes) if changes else 0.0


def _tail(seq: list, n: int) -> list:
    """Last min(n, len(seq)) items."""
    return seq[-min(n, len(seq)) :] if seq else []


def compute_stock_indicators(
    symbol: str,
    prices: list[StockPrice],
    from_date: datetime,
    to_date: datetime,
    sma_lookup: dict[int, float | None] | None = None,
    benchmark_changes_pct: dict[int, float] | None = None,
) -> StockIndicators:
    """Analyze stock price data and return weekly indicators.

    Optional inputs:
        sma_lookup: pre-loaded SMA value at `to_date` for each window
            (20/50/100/200). Missing/None windows produce 0.0 for the related fields.
        benchmark_changes_pct: pre-computed `change_pct_Nw` for the benchmark index
            (windows 4/13/26/52). Missing windows produce 0.0 for the related fields.
    """
    sma_lookup = sma_lookup or {}
    benchmark_changes_pct = benchmark_changes_pct or {}
    if not prices:
        raise ValueError(
            f"Insufficient data for {symbol} from {from_date.date()} to {to_date.date()}"
        )

    weekly_data = _aggregate_to_weekly(
        prices, date_from=from_date.date(), date_to=to_date.date()
    )

    if len(weekly_data) < 5:
        raise ValueError(
            f"Insufficient data for {symbol} from {from_date.date()} to {to_date.date()}"
        )

    if weekly_data[-1].week_ending < (to_date - timedelta(weeks=4)).date():
        raise ValueError(
            f"Insufficient data for {symbol} from {from_date.date()} to {to_date.date()}"
        )

    total_weeks = len(weekly_data)
    weekly_close = np.array([w.closing_price for w in weekly_data])

    # Period-over-period change series
    weekly_changes = [
        _calculate_pct_change(
            weekly_data[i - 1].closing_price, weekly_data[i].closing_price
        )
        for i in range(1, len(weekly_data))
    ]
    biweekly_changes = [
        _calculate_pct_change(
            weekly_data[i - 2].closing_price, weekly_data[i].closing_price
        )
        for i in range(2, len(weekly_data))
    ]
    monthly_changes = [
        _calculate_pct_change(
            weekly_data[i - 4].closing_price, weekly_data[i].closing_price
        )
        for i in range(4, len(weekly_data))
    ]

    # Slope & R² per window (linear)
    w13 = _tail(weekly_data, 13)
    w26 = _tail(weekly_data, 26)
    w52 = weekly_data
    slope_pct_13w, r_squared_13w = _linregress_slope_pct_r2(w13)
    slope_pct_26w, r_squared_26w = _linregress_slope_pct_r2(w26)
    slope_pct_52w, r_squared_52w = _linregress_slope_pct_r2(w52)

    # Log regression per window
    log_slope_13w, log_r_squared_13w = _log_slope_r2(w13)
    log_slope_26w, log_r_squared_26w = _log_slope_r2(w26)
    log_slope_52w, log_r_squared_52w = _log_slope_r2(w52)

    # 4-week R² (short-term trend consistency); slope at 4w is too noisy to keep
    w4 = _tail(weekly_data, 4)
    _, r_squared_4w = _linregress_slope_pct_r2(w4)

    # Max drawdown per window
    max_drawdown_pct_4w = _max_drawdown_pct(weekly_close[-min(4, len(weekly_close)) :])
    max_drawdown_pct_13w = _max_drawdown_pct(
        weekly_close[-min(13, len(weekly_close)) :]
    )
    max_drawdown_pct_26w = _max_drawdown_pct(
        weekly_close[-min(26, len(weekly_close)) :]
    )
    max_drawdown_pct_52w = _max_drawdown_pct(weekly_close)

    # % up-weeks per window
    pct_weeks_positive_4w = _pct_positive(_tail(weekly_changes, 4))
    pct_weeks_positive_13w = _pct_positive(_tail(weekly_changes, 13))
    pct_weeks_positive_26w = _pct_positive(_tail(weekly_changes, 26))
    pct_weeks_positive_52w = _pct_positive(weekly_changes)

    # Volatility (std-dev) over full series
    return_std_52w = float(np.std(weekly_changes)) if weekly_changes else 0.0
    negative_changes = [c for c in weekly_changes if c < 0]
    downside_std_52w = float(np.std(negative_changes)) if negative_changes else 0.0

    # Momentum acceleration over 13 weeks (recent half slope minus earlier half slope)
    if len(w13) >= 6:
        mid = len(w13) // 2
        w13_early = w13[:mid]
        w13_late = w13[mid:]
        x_early = np.arange(len(w13_early))
        y_early = np.array([w.closing_price for w in w13_early])
        s_early, _, _, _, _ = stats.linregress(x_early, y_early)
        x_late = np.arange(len(w13_late))
        y_late = np.array([w.closing_price for w in w13_late])
        s_late, _, _, _, _ = stats.linregress(x_late, y_late)
        base_price = w13[0].closing_price
        acceleration_pct_13w = (
            float(((s_late - s_early) / base_price) * 100) if base_price != 0 else 0.0
        )
    else:
        acceleration_pct_13w = 0.0

    # Distance from 4-week high (always <= 0)
    w4_prices = np.array([w.closing_price for w in w4]) if w4 else weekly_close[-1:]
    high_4w = float(np.max(w4_prices))
    current_price = weekly_data[-1].closing_price
    from_high_pct_4w = (
        float(((current_price - high_4w) / high_4w) * 100) if high_4w != 0 else 0.0
    )

    # Moving average structure: price relative to SMA windows
    def _price_vs_ma(period: int) -> float:
        sma_value = sma_lookup.get(period)
        if sma_value is None or sma_value == 0:
            return 0.0
        return float((current_price / sma_value - 1) * 100)

    price_vs_ma20_pct = _price_vs_ma(20)
    price_vs_ma50_pct = _price_vs_ma(50)
    price_vs_ma100_pct = _price_vs_ma(100)
    price_vs_ma200_pct = _price_vs_ma(200)

    sma50 = sma_lookup.get(50)
    sma200 = sma_lookup.get(200)
    if sma50 is not None and sma200 is not None and sma200 != 0:
        ma50_vs_ma200_pct = float((sma50 / sma200 - 1) * 100)
    else:
        ma50_vs_ma200_pct = 0.0

    # Relative strength vs benchmark (% point difference of N-week change)
    stock_change_pct_4w = _pt_change(weekly_data, 4)
    stock_change_pct_13w = _pt_change(weekly_data, 13)
    stock_change_pct_26w = _pt_change(weekly_data, 26)
    stock_change_pct_52w = _pt_change(weekly_data, 52)
    rs_pct_4w = stock_change_pct_4w - benchmark_changes_pct.get(4, 0.0)
    rs_pct_13w = stock_change_pct_13w - benchmark_changes_pct.get(13, 0.0)
    rs_pct_26w = stock_change_pct_26w - benchmark_changes_pct.get(26, 0.0)
    rs_pct_52w = stock_change_pct_52w - benchmark_changes_pct.get(52, 0.0)

    return StockIndicators(
        symbol=symbol,
        date=to_date.date(),
        total_weeks=total_weeks,
        # Slope
        slope_pct_13w=slope_pct_13w,
        slope_pct_26w=slope_pct_26w,
        slope_pct_52w=slope_pct_52w,
        # R²
        r_squared_4w=r_squared_4w,
        r_squared_13w=r_squared_13w,
        r_squared_26w=r_squared_26w,
        r_squared_52w=r_squared_52w,
        # Log slope / R²
        log_slope_13w=log_slope_13w,
        log_r_squared_13w=log_r_squared_13w,
        log_slope_26w=log_slope_26w,
        log_r_squared_26w=log_r_squared_26w,
        log_slope_52w=log_slope_52w,
        log_r_squared_52w=log_r_squared_52w,
        # Point-to-point change
        change_pct_1w=_pt_change(weekly_data, 1),
        change_pct_2w=_pt_change(weekly_data, 2),
        change_pct_4w=_pt_change(weekly_data, 4),
        change_pct_13w=_pt_change(weekly_data, 13),
        change_pct_26w=_pt_change(weekly_data, 26),
        change_pct_52w=_pt_change(weekly_data, 52),
        # Max swing
        max_jump_pct_1w=max(weekly_changes) if weekly_changes else 0.0,
        max_drop_pct_1w=-min(weekly_changes) if weekly_changes else 0.0,
        max_jump_pct_2w=max(biweekly_changes) if biweekly_changes else 0.0,
        max_drop_pct_2w=-min(biweekly_changes) if biweekly_changes else 0.0,
        max_jump_pct_4w=max(monthly_changes) if monthly_changes else 0.0,
        max_drop_pct_4w=-min(monthly_changes) if monthly_changes else 0.0,
        # Volatility std
        return_std_52w=return_std_52w,
        downside_std_52w=downside_std_52w,
        # Max drawdown
        max_drawdown_pct_4w=max_drawdown_pct_4w,
        max_drawdown_pct_13w=max_drawdown_pct_13w,
        max_drawdown_pct_26w=max_drawdown_pct_26w,
        max_drawdown_pct_52w=max_drawdown_pct_52w,
        # % up-weeks
        pct_weeks_positive_4w=pct_weeks_positive_4w,
        pct_weeks_positive_13w=pct_weeks_positive_13w,
        pct_weeks_positive_26w=pct_weeks_positive_26w,
        pct_weeks_positive_52w=pct_weeks_positive_52w,
        # Momentum shape
        acceleration_pct_13w=acceleration_pct_13w,
        from_high_pct_4w=from_high_pct_4w,
        # MA structure
        price_vs_ma20_pct=price_vs_ma20_pct,
        price_vs_ma50_pct=price_vs_ma50_pct,
        price_vs_ma100_pct=price_vs_ma100_pct,
        price_vs_ma200_pct=price_vs_ma200_pct,
        ma50_vs_ma200_pct=ma50_vs_ma200_pct,
        # Relative strength vs benchmark
        rs_pct_4w=rs_pct_4w,
        rs_pct_13w=rs_pct_13w,
        rs_pct_26w=rs_pct_26w,
        rs_pct_52w=rs_pct_52w,
    )


def rank_by_expression(
    items: list[StockIndicators],
    ranking_func: Callable[[StockIndicators], float],
) -> list[StockIndicators]:
    """Rank items by a user-defined ranking expression.

    Items are sorted by score descending (higher = better).
    """
    if len(items) <= 1:
        return items

    scored = [(ranking_func(item), item) for item in items]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


def slope_outlier_mask(
    items: list[StockIndicators], k: float = 3.0
) -> list[StockIndicators]:
    """Remove outliers based on the 52-week linear slope using modified Z-score (MAD)."""
    if not items or len(items) <= 2:
        return items

    slopes = np.asarray([i.slope_pct_52w for i in items], dtype=float)
    median = np.median(slopes)
    mad = np.median(np.abs(slopes - median))

    if mad == 0:
        return items

    modified_z = 0.6745 * (slopes - median) / mad
    return [item for item, ok in zip(items, np.abs(modified_z) <= 2.5) if ok]
