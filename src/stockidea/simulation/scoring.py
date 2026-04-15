"""Compute objective scores from simulation results for strategy evaluation."""

import math

import numpy as np

from stockidea.types import RebalanceHistory, SimulationScores


def compute_scores(
    rebalance_history: list[RebalanceHistory],
    rebalance_interval_weeks: int,
    initial_balance: float,
    final_balance: float,
    date_start_ts: float,
    date_end_ts: float,
) -> SimulationScores:
    """Compute objective scores from a simulation's rebalance history.

    Args:
        rebalance_history: List of rebalance periods with returns
        rebalance_interval_weeks: Weeks per rebalance period
        initial_balance: Starting portfolio value
        final_balance: Ending portfolio value
        date_start_ts: Simulation start as timestamp
        date_end_ts: Simulation end as timestamp
    """
    total_rebalances = len(rebalance_history)

    if total_rebalances == 0:
        return SimulationScores(
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_duration_weeks=0,
            win_rate=0.0,
            avg_win_pct=0.0,
            avg_loss_pct=0.0,
            total_rebalances=0,
        )

    # Per-period returns as fractions (not percentages)
    period_returns = np.array([r.profit_pct for r in rebalance_history])

    # Periods per year for annualization
    periods_per_year = 52.0 / rebalance_interval_weeks

    # --- Win rate ---
    wins = period_returns[period_returns > 0]
    losses = period_returns[period_returns <= 0]
    win_rate = float(len(wins) / total_rebalances)
    avg_win_pct = float(np.mean(wins) * 100) if len(wins) > 0 else 0.0
    avg_loss_pct = float(np.mean(losses) * 100) if len(losses) > 0 else 0.0

    # --- Sharpe ratio (annualized, risk-free = 0) ---
    mean_return = float(np.mean(period_returns))
    std_return = float(np.std(period_returns, ddof=1)) if total_rebalances > 1 else 0.0
    sharpe_ratio = (
        float(mean_return / std_return * math.sqrt(periods_per_year))
        if std_return > 0
        else 0.0
    )

    # --- Sortino ratio (annualized, downside deviation only) ---
    downside_returns = period_returns[period_returns < 0]
    downside_std = (
        float(np.std(downside_returns, ddof=1)) if len(downside_returns) > 1 else 0.0
    )
    sortino_ratio = (
        float(mean_return / downside_std * math.sqrt(periods_per_year))
        if downside_std > 0
        else 0.0
    )

    # --- Portfolio equity curve for drawdown ---
    equity = [initial_balance]
    for r in rebalance_history:
        equity.append(equity[-1] + r.profit)
    equity_arr = np.array(equity)

    peak = np.maximum.accumulate(equity_arr)
    drawdowns_pct = (equity_arr - peak) / peak * 100  # negative values
    max_drawdown_pct = float(-np.min(drawdowns_pct))

    # Max drawdown duration (in rebalance periods → weeks)
    max_dd_duration_periods = 0
    current_dd_duration = 0
    for i in range(len(equity_arr)):
        if equity_arr[i] < peak[i]:
            current_dd_duration += 1
            max_dd_duration_periods = max(max_dd_duration_periods, current_dd_duration)
        else:
            current_dd_duration = 0
    max_drawdown_duration_weeks = max_dd_duration_periods * rebalance_interval_weeks

    # --- Calmar ratio (annualized return / max drawdown) ---
    years = (date_end_ts - date_start_ts) / (365.25 * 24 * 3600)
    total_return = (final_balance - initial_balance) / initial_balance
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    calmar_ratio = (
        float(annualized_return / (max_drawdown_pct / 100))
        if max_drawdown_pct > 0
        else 0.0
    )

    return SimulationScores(
        sharpe_ratio=round(sharpe_ratio, 4),
        sortino_ratio=round(sortino_ratio, 4),
        calmar_ratio=round(calmar_ratio, 4),
        max_drawdown_pct=round(max_drawdown_pct, 4),
        max_drawdown_duration_weeks=max_drawdown_duration_weeks,
        win_rate=round(win_rate, 4),
        avg_win_pct=round(avg_win_pct, 4),
        avg_loss_pct=round(avg_loss_pct, 4),
        total_rebalances=total_rebalances,
    )
