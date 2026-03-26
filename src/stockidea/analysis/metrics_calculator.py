from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging

import numpy as np
from scipy import stats  # type: ignore

from stockidea.types import StockMetrics, StockPrice

logger = logging.getLogger(__name__)


@dataclass
class WeeklyData:
    """Represents one week's stock data."""

    week_ending: date
    closing_price: float


def _get_week_ending(d: date) -> date:
    """Get the Friday of the week for a given date."""
    # Friday is weekday 4
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

    Args:
        prices: List of daily StockPrice objects (most recent first)
        one_year_ago: Start date for analysis

    Returns:
        List of WeeklyData sorted by week_ending (oldest first)
    """
    filtered = [p for p in prices if p.date >= date_from and p.date <= date_to]
    filtered.sort(key=lambda x: x.date)

    if not filtered:
        return []

    # Group by week (using Friday as week end)
    weeks: dict[date, list[StockPrice]] = {}
    for price in filtered:
        week_end = _get_week_ending(price.date)
        if week_end not in weeks:
            weeks[week_end] = []
        weeks[week_end].append(price)

    # For each week, use the last trading day's closing price
    weekly_data = []
    for week_end, week_prices in sorted(weeks.items()):
        # Get the last trading day of the week
        last_day = max(week_prices, key=lambda x: x.date)
        weekly_data.append(
            WeeklyData(week_ending=week_end, closing_price=last_day.adj_close)
        )

    return weekly_data


def _calculate_pct_change(old: float, new: float) -> float:
    """Calculate percentage change from old to new value."""
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100


def _max_drawdown(prices_arr: np.ndarray) -> float:
    """Max peak-to-trough decline as a positive percentage."""
    if len(prices_arr) < 2:
        return 0.0
    peak = np.maximum.accumulate(prices_arr)
    drawdowns = (prices_arr - peak) / peak * 100
    return float(-np.min(drawdowns))


def _pct_positive(changes: list[float]) -> float:
    """Fraction of values greater than zero."""
    return sum(1 for c in changes if c > 0) / len(changes) if changes else 0.0


def _linregress_slope_r2(window: list[WeeklyData]) -> tuple[float, float]:
    """Linear regression slope (% of window starting price per week) and R²."""
    if len(window) < 3:
        return 0.0, 0.0
    x = np.arange(len(window))
    y = np.array([w.closing_price for w in window])
    slope, _, r_value, _, _ = stats.linregress(x, y)
    slope_pct = float((slope / window[0].closing_price) * 100) if window[0].closing_price != 0 else 0.0
    return slope_pct, float(r_value ** 2)


def compute_stock_metrics(
    symbol: str, prices: list[StockPrice], from_date: datetime, to_date: datetime
) -> StockMetrics:
    """
    Analyze stock price data and return weekly metrics.

    Args:
        prices: List of StockPrice objects (as returned by fetch_stock_prices)

    Returns:
        StockMetrics with all computed metrics, or None if insufficient data
    """
    if not prices:
        raise ValueError(f"Insufficient data for {symbol} from {from_date.date()} to {to_date.date()}")

    weekly_data = _aggregate_to_weekly(prices, date_from=from_date.date(), date_to=to_date.date())

    if len(weekly_data) < 5:
        raise ValueError(f"Insufficient data for {symbol} from {from_date.date()} to {to_date.date()}")

    if weekly_data[-1].week_ending < (to_date - timedelta(weeks=4)).date():
        raise ValueError(f"Insufficient data for {symbol} from {from_date.date()} to {to_date.date()}")

    total_weeks = len(weekly_data)
    weekly_close = np.array([w.closing_price for w in weekly_data])

    # ── Weekly change series ──────────────────────────────────────────────────
    weekly_changes = [
        _calculate_pct_change(weekly_data[i - 1].closing_price, weekly_data[i].closing_price)
        for i in range(1, len(weekly_data))
    ]
    biweekly_changes = [
        _calculate_pct_change(weekly_data[i - 2].closing_price, weekly_data[i].closing_price)
        for i in range(2, len(weekly_data))
    ]
    monthly_changes = [
        _calculate_pct_change(weekly_data[i - 4].closing_price, weekly_data[i].closing_price)
        for i in range(4, len(weekly_data))
    ]

    # ── Point-to-point change ─────────────────────────────────────────────────
    def _pt_change(n: int) -> float:
        n = min(n, len(weekly_data) - 1)
        return _calculate_pct_change(weekly_data[-n - 1].closing_price, weekly_data[-1].closing_price) if n > 0 else 0.0

    # ── Max jump / drop ───────────────────────────────────────────────────────
    def _max_jump(changes: list[float]) -> float:
        return max(changes) if changes else 0.0

    def _max_drop(changes: list[float]) -> float:
        return -min(changes) if changes else 0.0

    # ── Slope & R² per window ─────────────────────────────────────────────────
    slope_pct_13w, r_squared_13w = _linregress_slope_r2(weekly_data[-min(13, len(weekly_data)):])
    slope_pct_26w, r_squared_26w = _linregress_slope_r2(weekly_data[-min(26, len(weekly_data)):])
    slope_pct_52w, r_squared_52w = _linregress_slope_r2(weekly_data)

    # ── Log regression per window ─────────────────────────────────────────────
    def _log_slope_r2(window: list[WeeklyData]) -> tuple[float, float]:
        if len(window) < 3:
            return 0.0, 0.0
        x = np.arange(len(window))
        y = np.log(np.array([w.closing_price for w in window]))
        s, _, r, _, _ = stats.linregress(x, y)
        return float(s), float(r ** 2)

    log_slope_13w, log_r_squared_13w = _log_slope_r2(weekly_data[-min(13, len(weekly_data)):])
    log_slope_26w, log_r_squared_26w = _log_slope_r2(weekly_data[-min(26, len(weekly_data)):])
    log_slope_52w, log_r_squared_52w = _log_slope_r2(weekly_data)

    # ── Max drawdown per window ───────────────────────────────────────────────
    max_drawdown_pct_4w  = _max_drawdown(weekly_close[-min(4,  len(weekly_close)):])
    max_drawdown_pct_13w = _max_drawdown(weekly_close[-min(13, len(weekly_close)):])
    max_drawdown_pct_26w = _max_drawdown(weekly_close[-min(26, len(weekly_close)):])
    max_drawdown_pct_52w = _max_drawdown(weekly_close)

    # ── % up-weeks per window ─────────────────────────────────────────────────
    pct_weeks_positive_4w  = _pct_positive(weekly_changes[-min(4,  len(weekly_changes)):])
    pct_weeks_positive_13w = _pct_positive(weekly_changes[-min(13, len(weekly_changes)):])
    pct_weeks_positive_26w = _pct_positive(weekly_changes[-min(26, len(weekly_changes)):])
    pct_weeks_positive_52w = _pct_positive(weekly_changes)

    return StockMetrics(
        symbol=symbol,
        date=to_date.date(),
        total_weeks=total_weeks,
        # Slope
        slope_pct_13w=slope_pct_13w,
        slope_pct_26w=slope_pct_26w,
        slope_pct_52w=slope_pct_52w,
        # R²
        r_squared_13w=r_squared_13w,
        r_squared_26w=r_squared_26w,
        r_squared_52w=r_squared_52w,
        # Log trend
        log_slope_13w=log_slope_13w,
        log_r_squared_13w=log_r_squared_13w,
        log_slope_26w=log_slope_26w,
        log_r_squared_26w=log_r_squared_26w,
        log_slope_52w=log_slope_52w,
        log_r_squared_52w=log_r_squared_52w,
        # Point-to-point change
        change_pct_1w=_pt_change(1),
        change_pct_2w=_pt_change(2),
        change_pct_4w=_pt_change(4),
        change_pct_13w=_pt_change(13),
        change_pct_26w=_pt_change(26),
        change_pct_52w=_pt_change(52),
        # Max single-period swing
        max_jump_pct_1w=_max_jump(weekly_changes),
        max_drop_pct_1w=_max_drop(weekly_changes),
        max_jump_pct_2w=_max_jump(biweekly_changes),
        max_drop_pct_2w=_max_drop(biweekly_changes),
        max_jump_pct_4w=_max_jump(monthly_changes),
        max_drop_pct_4w=_max_drop(monthly_changes),
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
    )


def rank_by_rising_stability_score(items: list[StockMetrics]) -> list[StockMetrics]:
    """Rank items by rising stability score (slope * r² weighted)."""
    if len(items) <= 1:
        return items

    slopes = np.array([i.slope_pct_52w for i in items], dtype=float)
    r2s = np.array([i.r_squared_52w for i in items], dtype=float)

    slope_rank = slopes.argsort().argsort() / (len(slopes) - 1)
    r2_rank = r2s.argsort().argsort() / (len(r2s) - 1)

    scores = slope_rank * (r2_rank ** 1.7)

    return [item for _, item in sorted(zip(scores, items), key=lambda x: x[0], reverse=True)]


def slope_outlier_mask(items: list[StockMetrics], k: float = 3.0) -> list[StockMetrics]:
    """Remove outliers based on 52-week slope using modified Z-score."""
    if not items or len(items) <= 2:
        return items

    slopes = np.asarray([i.slope_pct_52w for i in items], dtype=float)
    median = np.median(slopes)
    mad = np.median(np.abs(slopes - median))

    if mad == 0:
        return items

    modified_z = 0.6745 * (slopes - median) / mad
    return [item for item, ok in zip(items, np.abs(modified_z) <= 2.5) if ok]
