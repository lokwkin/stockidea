"""FastAPI endpoints for stock analysis and simulations."""

from datetime import datetime, timedelta
from stockpick.config import OUTPUT_DIR
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import json
from pathlib import Path

import uvicorn

from stockpick.rule_engine import compile_rule
from stockpick.types import TrendAnalysis
from stockpick.datasource import market_data
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

SIMULATIONS_DIR = OUTPUT_DIR / "simulations"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"


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
def list_simulations() -> list[str]:
    """Return list of available simulation filenames (without .json extension)."""
    return _list_json_files(SIMULATIONS_DIR)


@app.get("/simulations/{filename}")
def get_simulation(filename: str) -> dict:
    """Return the full JSON content of a simulation file."""
    return _read_json_file(SIMULATIONS_DIR, filename)


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
            # Sort by trend_slope_pct (same as apply_rule does)
            filtered_analyses.sort(key=lambda x: x.annualized_slope, reverse=True)
            analyses = filtered_analyses
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid rule expression: {e}")

    # Convert back to dict format
    result_data = [a.model_dump() for a in analyses]

    return {
        "analysis_date": data["analysis_date"],
        "data": result_data,
    }


@app.get("/snp500")
def get_snp500_prices() -> list[dict]:
    """
    Fetch and return S&P 500 historical price data.

    Returns a list of price data points with date and price fields.
    """
    try:
        prices = market_data.get_stock_price_history(
            "^GSPC", from_date=datetime.now().date() - timedelta(weeks=1000), to_date=datetime.now().date())
        # Return data sorted by date (oldest first) for easier frontend consumption
        prices_sorted = sorted(prices, key=lambda x: x.date)
        return [
            {
                "date": price.date.isoformat(),
                "price": price.adj_close,
            }
            for price in prices_sorted
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch S&P 500 data: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
