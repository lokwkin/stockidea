
import csv
from pathlib import Path
from stockpick.config import DATA_DIR


DEFAULT_STOCKS_FILE = DATA_DIR / "stocks.txt"
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
