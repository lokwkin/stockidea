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

# =============================================================================
# Telegram bot (required only when running the bot)
# =============================================================================

TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
# The bot replies only to messages whose chat id matches this — single-user auth.
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")

# =============================================================================
# Strategy used by the Telegram bot's /pick handler
# =============================================================================

STRATEGY_RULE: str | None = os.getenv("STRATEGY_RULE")
STRATEGY_SORT: str | None = os.getenv("STRATEGY_SORT")  # None ⇒ DEFAULT_SORT
STRATEGY_MAX_STOCKS: int = int(os.getenv("STRATEGY_MAX_STOCKS", "3"))
STRATEGY_INDEX: str = os.getenv("STRATEGY_INDEX", "SP500")
# Stop-loss expression evaluated at buy time. Variables: buy_price,
# sma_20/50/100/200 (prior trading day). Examples: "buy_price * 0.95",
# "sma_50 * 0.95". Unset = no stop loss.
STRATEGY_STOP_LOSS_EXPR: str | None = os.getenv("STRATEGY_STOP_LOSS_EXPR")
