# Stockidea

Stockidea is a platform for designing and backtesting systematic stock strategies using transparent, composable signals. Users describe strategy ideas in natural language, and an AI agent translates them into concrete rules, iteratively backtests and refines them, and presents the best results. Users can then send follow-up instructions to further tune the strategy in a multi-turn conversation. The platform also supports manual rule-based portfolio construction with momentum, trend, volatility, and stability indicators.

## Table of Contents

- [Dashboard](#dashboard)
- [Architecture](#architecture)
  - [Datasource](#datasource)
  - [Indicators](#indicators)
  - [Backtest](#backtest)
  - [Agent](#agent)
- [Setup](#setup)
- [Stock Indicators and Rule Syntax](#stock-indicators-and-rule-syntax)
- [Backtest Scores](#backtest-scores)
- [License](#license)

## Dashboard

The frontend dashboard is organized around **Strategy Ideas**. Users create a strategy with a natural language instruction, and the AI agent designs, backtests, and iterates on it autonomously. Users can send follow-up instructions to refine the strategy further. All backtests from a strategy are linked and displayed in a comparison table for easy iteration tracking.

<img src="docs/dashboard.gif" alt="Dashboard" width="60%">

## Architecture

<img src="docs/architecture.svg" alt="Architecture" width="100%">

The project is organized around four core components: **Datasource**, **Indicators**, **Backtest**, and **Agent**. These are exposed through both a web dashboard (React + FastAPI) and a CLI.

### Datasource

Responsible for acquiring and storing all market data. Fetches stock prices, index prices, and index constituent history from [Financial Modeling Prep (FMP)](https://financialmodelingprep.com/) and persists them in PostgreSQL. Each symbol's data is tracked with a freshness timestamp -- data fetched within the last day is considered fresh and skipped on subsequent runs, so startup and manual refreshes only pull what's actually stale.

A key capability is **historical constituent reconstruction**: given any past date, the datasource can determine which stocks belonged to an index at that point in time using constituent change records. This is critical for survivorship-bias-free backtesting.

```bash
# Refresh all data (constituents + index prices + stock prices) for SP500 and NASDAQ
uv run python -m stockidea.cli fetch-data

# Or fetch individually
uv run python -m stockidea.cli fetch-constituents --index SP500
uv run python -m stockidea.cli fetch-index --index SP500
uv run python -m stockidea.cli fetch-prices --index SP500
```

### Indicators

Computes per-stock performance indicators from raw price data. Daily prices are aggregated into Friday-close weekly series, then indicators are calculated across four categories:

- **Returns** -- Point-to-point percentage changes at various horizons (1w, 2w, 4w, 13w, 26w, 1y)
- **Trend** -- Linear and log regression slopes with R² values, both full-period and windowed (13w, 26w)
- **Volatility** -- Maximum upward/downward swings at 1w, 2w, and 4w windows
- **Stability** -- Maximum drawdown, fraction of positive weeks

Users can write **rule expressions** against any of these fields to filter stocks (e.g. `change_13w_pct > 10 AND max_drop_2w_pct < 15`). Rules support comparison operators and `AND`/`OR` logic.

After filtering, the remaining stocks are sorted by a **ranking expression** — a numeric formula over the same indicator fields, where higher scores rank higher. The default is `change_13w_pct / weekly_return_std` (risk-adjusted momentum). Pass `--ranking` to override it: e.g. `--ranking 'linear_slope_pct * linear_r_squared'` for trend quality, or `--ranking 'change_26w_pct / max_drawdown_pct'` for return per unit of drawdown. Ranking matters whenever more stocks pass the filter than `--max-stocks` allows.

```bash
# Compute indicators for all SP500 constituents at a given date
uv run python -m stockidea.cli compute -d 2026-01-20

# Compute indicators and filter by a rule (uses the default ranking)
uv run python -m stockidea.cli pick -r 'change_13w_pct > 10 AND max_drop_2w_pct < 15'

# Filter and rank with a custom ranking expression
uv run python -m stockidea.cli pick \
  -r 'change_13w_pct > 10 AND max_drop_2w_pct < 15' \
  --ranking 'linear_slope_pct * linear_r_squared' \
  --max-stocks 5
```

### Backtest

The backtest engine that evaluates a strategy over a historical date range. At each rebalance point, it:

1. Computes indicators for all index constituents at that date
2. Filters stocks using the user's rule expression
3. Ranks and selects the top N stocks
4. Backtests buying equal-weight positions and selling at the next rebalance

The engine tracks portfolio value over time against a baseline index (S&P 500) and produces objective performance scores including Sharpe ratio, Sortino ratio, Calmar ratio, max drawdown, and win rate.

Backtests submitted through the web dashboard are processed asynchronously via a job queue -- the request is enqueued and a background worker picks it up, so long-running backtests don't block the API.

```bash
uv run python -m stockidea.cli backtest \
  --date-start=2022-01-01 \
  --date-end=2026-01-20 \
  --rule='change_13w_pct > 10 AND max_drop_2w_pct < 15'
```

### Agent

An AI-powered strategy designer that sits on top of the other three components. The workflow is **strategy-centric and conversational**:

1. The user creates a **Strategy Idea** with a natural language instruction (e.g. "I want a momentum strategy that avoids big drops")
2. The agent discovers available indicator fields and translates the idea into a concrete rule expression
3. The agent runs **5-10 backtest iterations** autonomously, adjusting thresholds and conditions based on performance scores and diagnostics
4. The agent presents the final recommendation with its performance summary
5. The user can send **follow-up instructions** (e.g. "try tighter drawdown", "focus on tech stocks") to trigger another round of agent fine-tuning with full conversation context

All backtests from a strategy are linked and displayed in a comparison table. The agent saves strategy notes to track reasoning and iteration history. Both the CLI and web dashboard create persistent strategies in the database.

Supports both Anthropic Claude and OpenAI GPT models (auto-detected from model name). On the web dashboard, the agent streams its reasoning, tool calls, and results in real time via SSE. Default backtest period is 3 years.

```bash
# Create a strategy and run the agent (saves to DB)
uv run python -m stockidea.cli agent -i "I want a momentum strategy that avoids big drops"
uv run python -m stockidea.cli agent -i "momentum strategy" -m gpt-5.4   # use OpenAI
```

## Setup

1. Clone a `.env` from `.env.example` and provide your own credentials.

```bash
cp .env.example .env
```

Required variables:
- `FMP_API_KEY` -- [Financial Modeling Prep](https://financialmodelingprep.com/) API key for market data
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` -- at least one is needed for the AI agent feature
- PostgreSQL credentials (defaults work with docker-compose)

2. Start PostgreSQL and the backend using docker-compose:

```bash
docker-compose up -d
```

3. Run database migrations:

```bash
uv run alembic upgrade head
```

4. Start the frontend dev server:

```bash
cd frontend && npm run dev
```

## Stock Indicators and Rule Syntax

### Available Indicator Fields

| Field | Description |
|-------|-------------|
| **Return indicators** | |
| `change_1w_pct` | Percentage change over 1 week |
| `change_2w_pct` | Percentage change over 2 weeks |
| `change_4w_pct` | Percentage change over 4 weeks |
| `change_13w_pct` | Percentage change over 13 weeks (~3 months) |
| `change_26w_pct` | Percentage change over 26 weeks (~6 months) |
| `change_1y_pct` | Percentage change over 1 year (52 weeks) |
| **Trend indicators** | |
| `linear_slope_pct` | Linear trend slope as % of starting price per week |
| `linear_r_squared` | R² of the linear trend fit (0--1, higher = more consistent) |
| `log_slope` | Annualized log trend slope |
| `log_r_squared` | R² of the log trend fit (0--1) |
| `slope_13w_pct` | Linear slope over last 13 weeks (% per week) |
| `r_squared_13w` | R² of 13-week regression |
| `r_squared_4w` | R² of 4-week regression (short-term trend consistency) |
| `slope_26w_pct` | Linear slope over last 26 weeks (% per week) |
| `r_squared_26w` | R² of 26-week regression |
| **Volatility indicators (max swings)** | |
| `max_jump_1w_pct` | Maximum 1-week percentage increase |
| `max_drop_1w_pct` | Maximum 1-week percentage decrease |
| `max_jump_2w_pct` | Maximum 2-week percentage increase |
| `max_drop_2w_pct` | Maximum 2-week percentage decrease |
| `max_jump_4w_pct` | Maximum 4-week percentage increase |
| `max_drop_4w_pct` | Maximum 4-week percentage decrease |
| **Volatility indicators (statistical)** | |
| `weekly_return_std` | Standard deviation of weekly returns (typical weekly variability) |
| `downside_std` | Standard deviation of negative weekly returns only (downside risk) |
| **Stability indicators** | |
| `max_drawdown_pct` | Maximum peak-to-trough drawdown (e.g. 18.5 = fell 18.5% from peak) |
| `pct_weeks_positive` | Fraction of weeks with positive returns (0.0--1.0) |
| `total_weeks` | Total number of weeks analyzed |
| **Momentum shape** | |
| `acceleration_13w` | Momentum acceleration over 13 weeks (positive = speeding up) |
| `pct_from_4w_high` | Distance from 4-week high in % (always <= 0, closer to 0 = near recent high) |

## Backtest Scores

Backtests produce the following performance scores:

| Score | Description |
|-------|-------------|
| Sharpe ratio | Risk-adjusted return (excess return / volatility) |
| Sortino ratio | Downside risk-adjusted return |
| Calmar ratio | Return / max drawdown |
| Max drawdown % | Largest peak-to-trough decline |
| Max drawdown duration | Longest drawdown period in weeks |
| Win rate | Fraction of profitable rebalance periods |
| Avg win / loss % | Average gain on wins and average loss on losses |

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
