"""Main entry point for stock analysis."""

import csv
from datetime import datetime, timedelta
import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from stockpick.config import DATA_DIR, OUTPUT_DIR

from stockpick.fetch_prices import (
    fetch_stock_prices,
)
from stockpick.price_analyzer import PriceAnalysis, analyze_stock
from stockpick.simulator import Simulator, SimulationResult

load_dotenv()

# Project paths
DEFAULT_STOCKS_FILE = DATA_DIR / "stocks.txt"  # noqa: F821
SP_500_FILE = DATA_DIR / "sp_500.csv"


def load_symbols(filepath: Path = DEFAULT_STOCKS_FILE) -> list[str]:
    """
    Load stock symbols from a text file (one symbol per line).

    Args:
        filepath: Path to the stocks file

    Returns:
        List of stock ticker symbols
    """
    with open(filepath) as f:
        return [line.strip() for line in f if line.strip()]


def load_sp_500(filepath: Path = SP_500_FILE) -> list[str]:
    """
    Load S&P 500 stock symbols from the CSV file.

    Args:
        filepath: Path to the sp_500.csv file

    Returns:
        List of S&P 500 stock ticker symbols
    """
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        return [row["Symbol"] for row in reader]


def rule_1(analysis: PriceAnalysis) -> bool:
    return (
        analysis.trend_slope_pct > 1.5
        and analysis.trend_r_squared > 0.8
        and analysis.biggest_weekly_drop_pct > -10
        and analysis.biggest_biweekly_drop_pct > -15
        and analysis.biggest_monthly_drop_pct > -15
        and analysis.change_3m_pct > 0
        and analysis.change_6m_pct > 0
        and analysis.overall_change_pct > 0
    )


def generate_report():
    symbols = load_sp_500()
    analysis_date = datetime.now()
    analyses: list[PriceAnalysis] = []

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Analyzing {symbol}...", end="\r")
        try:
            prices = fetch_stock_prices(symbol)
            analysis = analyze_stock(prices, today=analysis_date.date())
            analyses.append(analysis)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            continue

    # Filter out None analyses
    valid_analyses = [a for a in analyses if a is not None]
    print(f"\nAnalyzed {len(valid_analyses)} stocks successfully")

    # Save analysis data to JSON
    analysis_path = OUTPUT_DIR / f"analysis_{datetime.now().strftime('%Y%m%d')}.json"
    analysis_data = [asdict(a) for a in valid_analyses]
    analysis_path.write_text(
        json.dumps(
            {
                "analysis_date": analysis_date.strftime("%Y%m%d"),
                "data": analysis_data,
            },
            indent=2,
        )
    )
    print(f"✓ Analysis saved: {analysis_path}")


def save_simulation_result(result: SimulationResult, criteria_name: str) -> None:
    """Save simulation result to JSON file in output directory."""

    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    result_dict = asdict(result)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"simulation_{criteria_name}_{timestamp}.json"
    output_path.write_text(json.dumps(result_dict, indent=2, default=serialize))
    print(f"✓ Simulation result saved: {output_path}")


def simulate():
    """Fetch and analyze stock prices, then generate HTML report."""
    symbols = load_sp_500()

    simulator = Simulator(
        criteria=[],
        max_stocks=3,
        rebalance_interval_weeks=2,
        date_start=datetime.now() - timedelta(weeks=52 * 4),
        date_end=datetime.now() - timedelta(weeks=52 * 0),
    )
    simulator.load_stock_prices(symbols)

    criteria_list: list[Callable[[PriceAnalysis], bool]] = [rule_1]
    for criteria in criteria_list:
        simulation_result = simulator.simulate(criteria=criteria)
        print(
            f"Simulation result: {simulation_result.profit_pct * 100:2.2f}%, {simulation_result.profit:2.2f}"
        )
        save_simulation_result(simulation_result, criteria.__name__)


if __name__ == "__main__":
    simulate()
