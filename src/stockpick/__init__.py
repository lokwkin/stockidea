"""Stock analysis and reporting package."""

from .fetch_prices import StockPrice, fetch_stock_prices, fetch_stock_prices_batch
from .analysis.price_analyzer import PriceAnalysis, analyze_stock
from .analysis.analysis import generate_report
from .simulation.simulator import Simulator, SimulationResult
from .simulation.simulation import save_simulation_result
from . import stock_loader

__all__ = [
    "StockPrice",
    "fetch_stock_prices",
    "fetch_stock_prices_batch",
    "PriceAnalysis",
    "analyze_stock",
    "generate_report",
    "Simulator",
    "SimulationResult",
    "save_simulation_result",
    "stock_loader",
]
