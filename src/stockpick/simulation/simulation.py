from datetime import datetime, timedelta
import json
from dataclasses import asdict
from typing import Callable

from stockpick.analysis.price_analyzer import PriceAnalysis
from stockpick.simulation.simulator import Simulator, SimulationResult
import stockpick.stock_loader as stock_loader
from stockpick.config import OUTPUT_DIR


def save_simulation_result(result: SimulationResult, criteria_name: str) -> None:
    """Save simulation result to JSON file in output directory."""

    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    result_dict = asdict(result)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / "simulations" / f"simulation_{criteria_name}_{timestamp.format('%Y%m%d%H%M%S')}.json"
    output_path.write_text(json.dumps(result_dict, indent=2, default=serialize))
    print(f"✓ Simulation result saved: {output_path}")


def simulate(criteria_list: list[Callable[[PriceAnalysis], bool]]):
    """Fetch and analyze stock prices, then generate HTML report."""
    symbols = stock_loader.load_sp_500()

    simulator = Simulator(
        max_stocks=3,
        rebalance_interval_weeks=2,
        date_start=datetime.now() - timedelta(weeks=52 * 4),
        date_end=datetime.now() - timedelta(weeks=52 * 0),
    )
    simulator.load_stock_prices(symbols)

    for criteria in criteria_list:
        simulation_result = simulator.simulate(criteria=criteria)
        print(
            f"Simulation result: {simulation_result.profit_pct * 100:2.2f}%, {simulation_result.profit:2.2f}"
        )
        save_simulation_result(simulation_result, criteria.__name__)
