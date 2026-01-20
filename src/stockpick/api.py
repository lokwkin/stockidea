"""FastAPI endpoints for stock analysis and simulations."""

from stockpick.config import OUTPUT_DIR
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import json
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv()

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
def get_analysis(filename: str) -> dict:
    """Return the full JSON content of an analysis file."""
    return _read_json_file(ANALYSIS_DIR, filename)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
