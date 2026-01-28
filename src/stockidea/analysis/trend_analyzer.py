"""Analyze stock price data with weekly metrics."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
from scipy import stats  # type: ignore

from stockidea.types import TrendAnalysis, StockPrice


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


def analyze_stock(
    symbol: str, prices: list[StockPrice], from_date: datetime, to_date: datetime
) -> TrendAnalysis | None:
    """
    Analyze stock price data and return weekly metrics.

    Args:
        prices: List of StockPrice objects (as returned by fetch_stock_prices)

    Returns:
        TrendAnalysis with all computed metrics, or None if insufficient data
    """
    if not prices:
        return None

    weekly_data = _aggregate_to_weekly(prices, date_from=from_date.date(), date_to=to_date.date())

    if len(weekly_data) < 5:
        return None

    total_weeks = len(weekly_data)

    # Calculate weeks above previous periods
    weeks_above_1 = 0
    weeks_above_2 = 0
    weeks_above_4 = 0

    for i, week in enumerate(weekly_data):
        if i >= 1 and week.closing_price > weekly_data[i - 1].closing_price:
            weeks_above_1 += 1
        if i >= 2 and week.closing_price > weekly_data[i - 2].closing_price:
            weeks_above_2 += 1
        if i >= 4 and week.closing_price > weekly_data[i - 4].closing_price:
            weeks_above_4 += 1

    # Calculate weekly changes (percentage)
    weekly_changes = []
    for i in range(1, len(weekly_data)):
        change = _calculate_pct_change(
            weekly_data[i - 1].closing_price, weekly_data[i].closing_price
        )
        weekly_changes.append(change)

    # Calculate biweekly changes (percentage)
    biweekly_changes = []
    for i in range(2, len(weekly_data)):
        change = _calculate_pct_change(
            weekly_data[i - 2].closing_price, weekly_data[i].closing_price
        )
        biweekly_changes.append(change)

    # Calculate monthly changes (4 weeks, percentage)
    monthly_changes = []
    for i in range(4, len(weekly_data)):
        change = _calculate_pct_change(
            weekly_data[i - 4].closing_price, weekly_data[i].closing_price
        )
        monthly_changes.append(change)

    # Find biggest movements
    biggest_weekly_jump = max(weekly_changes) if weekly_changes else 0.0
    biggest_weekly_drop = min(weekly_changes) if weekly_changes else 0.0
    biggest_biweekly_jump = max(biweekly_changes) if biweekly_changes else 0.0
    biggest_biweekly_drop = min(biweekly_changes) if biweekly_changes else 0.0
    biggest_monthly_jump = max(monthly_changes) if monthly_changes else 0.0
    biggest_monthly_drop = min(monthly_changes) if monthly_changes else 0.0

    # Overall change (first week to last week)
    weeks_1y = min(52, len(weekly_data) - 1)
    change_1y = _calculate_pct_change(
        weekly_data[-weeks_1y - 1].closing_price, weekly_data[-1].closing_price
    )

    # 6-month change (approximately 26 weeks)
    weeks_6m = min(26, len(weekly_data) - 1)
    change_6m = (
        _calculate_pct_change(
            weekly_data[-weeks_6m - 1].closing_price, weekly_data[-1].closing_price
        )
        if weeks_6m > 0
        else 0.0
    )

    # 3-month change (approximately 13 weeks)
    weeks_3m = min(13, len(weekly_data) - 1)
    change_3m = (
        _calculate_pct_change(
            weekly_data[-weeks_3m - 1].closing_price, weekly_data[-1].closing_price
        )
        if weeks_3m > 0
        else 0.0
    )

    weeks_1m = min(4, len(weekly_data) - 1)
    change_1m = (
        _calculate_pct_change(
            weekly_data[-weeks_1m - 1].closing_price, weekly_data[-1].closing_price
        )
        if weeks_1m > 0
        else 0.0
    )

    # Trend analysis using linear regression
    # x = week number (0, 1, 2, ...), y = closing price
    x = np.arange(len(weekly_data))
    weekly_close = np.array([w.closing_price for w in weekly_data])
    log_weekly_close = np.log(weekly_close)

    log_slope, _log_intercept, log_r_value, _log_p_value, _log_std_err = stats.linregress(x, log_weekly_close)
    log_r_squared = log_r_value**2

    linear_slope, _linear_intercept, linear_r_value, _linear_p_value, _linear_std_err = stats.linregress(
        x, weekly_close)
    # Convert slope to percentage of starting price (per week)
    # weekly_slope = stats.linregress(x, y)
    starting_price = weekly_data[0].closing_price
    linear_slope_pct = (linear_slope / starting_price) * 100 if starting_price != 0 else 0.0

    # R² is r_value squared
    linear_r_squared = linear_r_value**2

    return TrendAnalysis(
        symbol=symbol,
        weeks_above_1_week_ago=weeks_above_1,
        weeks_above_2_weeks_ago=weeks_above_2,
        weeks_above_4_weeks_ago=weeks_above_4,
        biggest_weekly_jump_pct=biggest_weekly_jump,
        biggest_weekly_drop_pct=biggest_weekly_drop,
        biggest_biweekly_jump_pct=biggest_biweekly_jump,
        biggest_biweekly_drop_pct=biggest_biweekly_drop,
        biggest_monthly_jump_pct=biggest_monthly_jump,
        biggest_monthly_drop_pct=biggest_monthly_drop,
        change_1y_pct=change_1y,
        change_6m_pct=change_6m,
        change_3m_pct=change_3m,
        change_1m_pct=change_1m,
        total_weeks=total_weeks,
        linear_slope_pct=linear_slope_pct,
        linear_r_squared=linear_r_squared,
        log_slope=log_slope,
        log_r_squared=log_r_squared,
    )


def rank_by_rising_stability_score(items: list[TrendAnalysis]) -> list[TrendAnalysis]:

    slopes = np.array([i.linear_slope_pct for i in items], dtype=float)
    r2s = np.array([i.linear_r_squared for i in items], dtype=float)

    # Rank normalization (percentiles in [0, 1])
    slope_rank = slopes.argsort().argsort() / (len(slopes) - 1)
    r2_rank = r2s.argsort().argsort() / (len(r2s) - 1)

    # Combine: "must rise AND be stable", slightly overweight stability
    scores = slope_rank * (r2_rank ** 1.7)

    ranked_items = [
        item for _, item in
        sorted(zip(scores, items), key=lambda x: x[0], reverse=True)
    ]

    return ranked_items
