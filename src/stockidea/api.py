from datetime import datetime, timedelta
import logging
from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException

import uvicorn

from stockidea.analysis import metrics, metrics_calculator
from stockidea.rule_engine import compile_rule, extract_involved_keys
from stockidea.simulation.simulator import Simulator
from stockidea.types import SimulationConfig, StockIndex
from stockidea.datasource import constituent, market_data
from stockidea.datasource.database import conn, queries
from typing import Optional


logger = logging.getLogger(__name__)


app = FastAPI(title="StockPick API", version="0.1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/simulations")
async def list_simulations() -> list[dict]:
    """Return list of available simulations from database."""
    async with conn.get_db_session() as db_session:
        simulations = await queries.list_simulations(db_session)
        return simulations


@app.get("/simulations/{simulation_id}")
async def get_simulation(simulation_id: UUID) -> dict:
    """Return the full JSON content of a simulation by ID."""
    async with conn.get_db_session() as db_session:
        simulation_result = await queries.get_simulation_by_id(db_session, simulation_id)
        if simulation_result is None:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
        return simulation_result.model_dump()


@app.get("/metrics")
async def list_analysis() -> list[str]:
    dates = await metrics.list_metrics_dates()
    return [date.strftime("%Y-%m-%d") for date in dates]


@app.get("/metrics/{date}/")
async def get_analysis(date: str, rule: Optional[str] = None, index: StockIndex = StockIndex.SP500) -> dict:

    metrics_date = datetime.strptime(date, "%Y-%m-%d")
    # Get the symbols of the constituent
    symbols = await constituent.get_constituent_at(index, metrics_date.date())

    # Analyze the stock prices and save to database
    stock_metrics_batch = await metrics.get_stock_metrics_batch(
        symbols=symbols, metrics_date=metrics_date, back_period_weeks=52)

    # Apply rule if provided
    if rule:
        try:
            rule_func = compile_rule(rule)
            # Filter analyses using the rule (no max_stocks limit for API)
            stock_metrics_batch = [stock_metric for stock_metric in stock_metrics_batch if rule_func(stock_metric)]
            # Sort by rising stability score
            stock_metrics_batch = metrics_calculator.rank_by_rising_stability_score(stock_metrics_batch)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    return {
        "date": metrics_date.strftime("%Y-%m-%d"),
        "data": [stock_metric.model_dump() for stock_metric in stock_metrics_batch],
    }


@app.post("/simulate")
async def simulate(simulation_config: SimulationConfig) -> dict:
    """
    Simulate an investment strategy.
    """
    # Populate involved_keys from rule if not provided
    if not simulation_config.involved_keys:
        simulation_config.involved_keys = extract_involved_keys(simulation_config.rule)

    async with conn.get_db_session() as db_session:
        simulator = Simulator(
            db_session=db_session,
            max_stocks=simulation_config.max_stocks,
            rebalance_interval_weeks=simulation_config.rebalance_interval_weeks,
            date_start=simulation_config.date_start,
            date_end=simulation_config.date_end,
            rule_func=compile_rule(simulation_config.rule),
            rule_raw=simulation_config.rule,
            from_index=simulation_config.index,
            baseline_index=StockIndex.SP500,
        )
        simulation_result = await simulator.simulate()
        simulation_id = await queries.save_simulation_result(db_session, simulation_result)

    result_dict = simulation_result.model_dump()
    result_dict["id"] = simulation_id
    return result_dict


@app.get("/snp500")
async def get_snp500_prices() -> list[dict]:
    """
    Fetch and return S&P 500 historical price data.

    Returns a list of price data points with date and price fields.
    """
    async with conn.get_db_session() as db_session:
        try:
            prices = await market_data.get_index_prices(db_session, StockIndex.SP500, datetime.now() - timedelta(weeks=700), datetime.now())
            return [price.model_dump() for price in prices]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch S&P 500 data: {str(e)}"
            )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
