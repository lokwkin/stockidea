"""All environment variables and derived constants, loaded once via dotenv."""

import os

from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# FMP (Financial Modeling Prep)
# =============================================================================

FMP_API_KEY: str | None = os.getenv("FMP_API_KEY")
FMP_BASE_URL: str = "https://financialmodelingprep.com"

# =============================================================================
# PostgreSQL
# =============================================================================

POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "database")
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")

DATABASE_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# =============================================================================
# LLM API Keys (optional — required only when using the AI agent)
# =============================================================================

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
