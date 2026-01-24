from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import sys

# Force unbuffered output BEFORE anything else
os.environ["PYTHONUNBUFFERED"] = "1"
# Reopen stderr as unbuffered
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)


load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
_OUTPUT_DIR = PROJECT_ROOT / "output"
ANALYSIS_DIR = _OUTPUT_DIR / "analysis"
CACHE_DIR = PROJECT_ROOT / ".cache"

FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE_URL = "https://financialmodelingprep.com"

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "stockidea")
POSTGRES_USER = os.getenv("POSTGRES_USER", "stockidea")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "stockidea")

# Database URL for SQLAlchemy
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


class FlushHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application."""
    handler = FlushHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logging.root.handlers = []
    logging.root.addHandler(handler)
    logging.root.setLevel(level)

    # logging.basicConfig(
    #     level=level,
    #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    #     datefmt='%Y-%m-%d %H:%M:%S',
    #     stream=sys.stderr,
    #     force=True,  # Override any existing configuration
    #     # handlers=[FlushHandler()],
    # )


# Initialize logging on module import
setup_logging()
