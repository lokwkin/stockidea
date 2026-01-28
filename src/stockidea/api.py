"""FastAPI endpoints for stock analysis and simulations."""

from datetime import datetime, timedelta
from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import json
from pathlib import Path

import uvicorn

from stockidea.analysis import trend_analyzer
from stockidea.config import ANALYSIS_DIR
from stockidea.rule_engine import compile_rule, extract_involved_keys
from stockidea.simulation.simulator import Simulator
from stockidea.types import SimulationConfig, StockIndex, TrendAnalysis
from stockidea.datasource import market_data
from stockidea.datasource.database import conn, queries
from typing import Optional

app = FastAPI(title="StockPick API", version="0.1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _list_json_files(directory: Path) -> list[str]:
    """List JSON files in a directory, returning filenames without .json extension."""
    if not directory.exists():
        return []
    return sorted(
        [f.stem for f in directory.glob("*.json")],
        reverse=True,  # Most recent first
    )


def _read_json_file(directory: Path, filename: str) -> dict:
    """Read and return JSON content from a file."""
    filepath = directory / f"{filename}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return json.loads(filepath.read_text())


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


@app.get("/analysis")
def list_analysis() -> list[str]:
    """Return list of available analysis filenames (without .json extension)."""
    return _list_json_files(ANALYSIS_DIR)


@app.get("/analysis/{filename}")
def get_analysis(filename: str, rule: Optional[str] = None) -> dict:
    """
    Return the full JSON content of an analysis file.

    If rule is provided, applies the rule to filter the trend analysis results.
    """
    data = _read_json_file(ANALYSIS_DIR, filename)

    # Convert JSON data to TrendAnalysis objects
    analyses = [TrendAnalysis(**item) for item in data["data"]]

    # Apply rule if provided
    if rule:
        try:
            rule_func = compile_rule(rule)
            # Filter analyses using the rule (no max_stocks limit for API)
            filtered_analyses = [a for a in analyses if rule_func(a)]
            # Sort by rising stability score
            analyses = trend_analyzer.rank_by_rising_stability_score(filtered_analyses)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid rul expression: {e}")

    # Convert back to dict format
    result_data = [a.model_dump() for a in analyses]

    return {
        "analysis_date": data["analysis_date"],
        "data": result_data,
    }


@app.post("/simulate")
async def simulate(simulation_config: SimulationConfig) -> dict:
    """
    Simulate an investment strategy.
    """
    # Populate involved_keys from rule if not provided
    if not simulation_config.involved_keys:
        simulation_config.involved_keys = extract_involved_keys(simulation_config.rule)
    
    simulator = Simulator(
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

    async with conn.get_db_session() as db_session:
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
    try:
        prices = await market_data.get_index_prices(StockIndex.SP500, datetime.now() - timedelta(weeks=700), datetime.now())
        return [price.model_dump() for price in prices]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch S&P 500 data: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
