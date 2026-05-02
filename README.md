# Stockidea

Stockidea is a platform for designing and backtesting systematic stock strategies using transparent, composable signals. Users describe strategy ideas in natural language, and an AI agent translates them into concrete rules, iteratively backtests and refines them, and presents the best results. Users can then send follow-up instructions to further tune the strategy in a multi-turn conversation. The platform also supports manual rule-based portfolio construction with momentum, trend, volatility, and stability indicators.

## Table of Contents

- [Dashboard](#dashboard)
- [Architecture](#architecture)
  - [Datasource](#datasource)
  - [Indicators](#indicators)
  - [Screener](#screener)
  - [Backtest](#backtest)
  - [Agent](#agent)
  - [Telegram Bot](#telegram-bot)
- [Setup](#setup)
- [Stock Indicators and Rule Syntax](#stock-indicators-and-rule-syntax)
- [Backtest Scores](#backtest-scores)
- [License](#license)

## Dashboard

The frontend dashboard is organized around **Strategy Ideas**. Users create a strategy with a natural language instruction, and the AI agent designs, backtests, and iterates on it autonomously. Users can send follow-up instructions to refine the strategy further. All backtests from a strategy are linked and displayed in a comparison table for easy iteration tracking.

<img src="docs/agent.gif" alt="Agent strategy workflow" width="100%">

## Architecture

The project is organized around six core components: **Datasource**, **Indicators**, **Screener**, **Backtest**, **Agent**, and the **Telegram Bot**. These are exposed through both a web dashboard (React + FastAPI) and a CLI.

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

Computes per-stock performance indicators from raw price data. Daily prices are aggregated into Friday-close weekly series, then indicators are calculated across multiple categories:

- **Returns** -- Point-to-point percentage changes at various horizons (1w, 2w, 4w, 13w, 26w, 52w)
- **Trend** -- Linear and log regression slopes with R² values across windowed horizons (13w, 26w, 52w)
- **Volatility** -- Maximum upward/downward swings at 1w, 2w, and 4w windows; weekly-return standard deviation (incl. downside-only)
- **Stability** -- Maximum drawdown across windows (4w, 13w, 26w, 52w), fraction of positive weeks across windows
- **Moving average structure** -- Price vs 20/50/100/200-day SMAs and the 50/200 cross ratio (golden/death cross territory)

Users can write **rule expressions** against any of these fields to filter stocks (e.g. `change_pct_13w > 10 AND max_drop_pct_2w < 15`). Rules support comparison operators and `AND`/`OR` logic.

After filtering, the remaining stocks are sorted by a **sort expression** — a numeric formula over the same indicator fields, where higher scores rank higher. The default is `change_pct_13w / return_std_52w` (risk-adjusted momentum). Pass `--sort` (or `-s`) to override it: e.g. `--sort 'slope_pct_52w * r_squared_52w'` for trend quality, or `--sort 'change_pct_26w / max_drawdown_pct_52w'` for return per unit of drawdown. The sort expression matters whenever more stocks pass the filter than `--max-stocks` allows.

```bash
# Compute indicators for all SP500 constituents at a given date
uv run python -m stockidea.cli compute -d 2026-01-20
```

### Screener

Given a date and a strategy (rule + sort expression), the screener returns the top-N stocks to hold along with the buy price (Monday-open) and an optional per-position stop-loss price. When given a **portfolio** (cash + current holdings), it also sizes each pick (equal-weight allocation across `total_value = cash + Σ(qty × current_price)`) and emits the exact **buy/sell deltas** needed to rebalance into the new picks.

This is the same picking + sizing logic that the [Backtest](#backtest) engine drives at every rebalance, exposed as a standalone command for live trading decisions and reused by the [Telegram Bot](#telegram-bot).

Stop-loss is configured via either `--stop-loss-pct` (% below buy price) or `--stop-loss-ma PERIOD:PERCENT` (% of an SMA at buy time, e.g. `50:95` = 95% of the 50-day SMA). The two are mutually exclusive.

```bash
# Pick top-3 stocks for today (no portfolio sizing)
uv run python -m stockidea.cli pick -r 'change_pct_13w > 10 AND max_drop_pct_2w < 15'

# With a custom sort expression and a 5% stop loss
uv run python -m stockidea.cli pick \
  -r 'change_pct_13w > 10 AND max_drop_pct_2w < 15' \
  --sort 'slope_pct_52w * r_squared_52w' \
  --max-stocks 5 \
  --stop-loss-pct 5

# Size against a portfolio — emits target_quantity per pick + buy/sell deltas
uv run python -m stockidea.cli pick \
  -r 'change_pct_13w > 10' \
  --cash 10000 \
  --holding AAPL:5 --holding MSFT:10 \
  --stop-loss-ma 50:95
```

### Backtest

The backtest engine that evaluates a strategy over a historical date range. At each rebalance point, it:

1. Computes indicators for all index constituents at that date
2. Filters stocks using the user's rule expression
3. Sorts the survivors and selects the top N stocks
4. Buys equal-weight positions on Monday-open and holds for the rebalance interval, then sells

Each position can be exited early by an optional **stop-loss** (`--stop-loss-pct` for % below buy price, or `--stop-loss-ma PERIOD:PERCENT` for % of an SMA at buy time). End-of-period sells use either the previous Friday's adjusted close or the next-rebalance Monday's open, controlled by `--sell-timing`. The rebalance cadence is set by `--rebalance-interval-weeks` (default 2) and the position count by `--max-stocks` (default 3).

A per-fill **slippage** friction is applied symmetrically to every buy, period-end sell, and stop-loss exit (default 0.5%, configured via `--slippage-pct`) — the same friction is applied to the baseline so the comparison stays apples-to-apples.

The engine tracks portfolio value over time against a baseline index (SP500 proxied by SPY using FMP's dividend-adjusted endpoint, so baseline returns include reinvested dividends like the per-stock returns) and produces objective performance scores including Sharpe ratio, Sortino ratio, Calmar ratio, max drawdown, and win rate.

Backtests submitted through the web dashboard run synchronously inside the `POST /backtest` request -- the engine executes the full date range and returns the result in the response.

<img src="docs/backtest.gif" alt="Backtest workflow">

```bash
uv run python -m stockidea.cli backtest \
  --date-start=2022-01-01 \
  --date-end=2026-01-20 \
  --rule='change_pct_13w > 10 AND max_drop_pct_2w < 15' \
  --sort='change_pct_13w / return_std_52w' \
  --max-stocks 3 \
  --rebalance-interval-weeks 2 \
  --stop-loss-pct 5 \
  --sell-timing friday_close \
  --slippage-pct 0.5
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

### Telegram Bot

A long-running personal trading assistant on top of the [Screener](#screener). Send `/pick` to your bot with your current portfolio, and it replies with the buy/sell orders to place — useful for getting rebalance recommendations from your phone without running the CLI.

The strategy (rule, sort expression, max stocks, index, stop loss) is configured **once** via env vars at bot startup, so each `/pick` only needs the live portfolio. The bot is single-user by design: it only responds to messages from `TELEGRAM_CHAT_ID` and silently ignores everything else.

Required env vars:
- `TELEGRAM_BOT_TOKEN` -- token from [@BotFather](https://t.me/BotFather)
- `TELEGRAM_CHAT_ID` -- your own chat id (message `@userinfobot` to look it up)
- `STRATEGY_RULE` -- the filter expression (required)
- `STRATEGY_SORT`, `STRATEGY_MAX_STOCKS`, `STRATEGY_INDEX`, `STRATEGY_STOP_LOSS_PCT`, `STRATEGY_STOP_LOSS_MA` -- optional strategy knobs

```bash
# Start the bot (long-running; foreground)
uv run python -m stockidea.cli telegram run-bot
```

Send the bot a single-line message — all tokens are optional and order-independent:

```
/pick 5 NASDAQ $:10000 AAPL:5 MSFT:10
```

| Token          | Meaning                                                  |
| -------------- | -------------------------------------------------------- |
| `N` (integer)  | Override `STRATEGY_MAX_STOCKS` for this call             |
| `SP500`/`NASDAQ` | Override `STRATEGY_INDEX` for this call                |
| `$:N`          | Cash available                                           |
| `SYMBOL:QTY`   | Current holding                                          |

The reply echoes the active rule / sort / stop-loss / index / max stocks, then lists the picks. When at least one `SYMBOL:QTY` is provided, the reply also adds Sell/Buy sections with the deltas needed to rebalance — and pick lines include the target quantity. When no holdings are given, picks show only the price (no quantity, no Sell/Buy diff).

## Setup

1. Clone a `.env` from `.env.example` and provide your own credentials.

```bash
cp .env.example .env
```

Required variables:
- `FMP_API_KEY` -- [Financial Modeling Prep](https://financialmodelingprep.com/) API key for market data
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` -- at least one is needed for the AI agent feature
- PostgreSQL credentials (defaults work with docker-compose)

Optional variables (only needed when running the Telegram bot):
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` -- bot credentials and the single authorized chat id
- `STRATEGY_RULE`, `STRATEGY_SORT`, `STRATEGY_MAX_STOCKS`, `STRATEGY_INDEX`, `STRATEGY_STOP_LOSS_PCT`, `STRATEGY_STOP_LOSS_MA` -- the strategy used by `/pick`

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

All indicator fields follow a `<metric>_<unit>_<window>` naming convention so you can read the field and immediately know what it measures, in what units, over what horizon.

| Field | Description |
|-------|-------------|
| **Return indicators** | |
| `change_pct_1w` | Percentage change over 1 week |
| `change_pct_2w` | Percentage change over 2 weeks |
| `change_pct_4w` | Percentage change over 4 weeks |
| `change_pct_13w` | Percentage change over 13 weeks (~3 months) |
| `change_pct_26w` | Percentage change over 26 weeks (~6 months) |
| `change_pct_52w` | Percentage change over 52 weeks (~1 year) |
| **Trend indicators (linear regression)** | |
| `slope_pct_13w` | Linear slope over last 13 weeks (% per week) |
| `slope_pct_26w` | Linear slope over last 26 weeks (% per week) |
| `slope_pct_52w` | Linear slope over last 52 weeks (% per week) |
| `r_squared_4w` | R² of 4-week regression (very short-term trend consistency) |
| `r_squared_13w` | R² of 13-week regression |
| `r_squared_26w` | R² of 26-week regression |
| `r_squared_52w` | R² of 52-week regression |
| **Trend indicators (log regression)** | |
| `log_slope_13w` | Log-regression slope over last 13 weeks (compounded growth rate per week) |
| `log_r_squared_13w` | R² of 13-week log regression |
| `log_slope_26w` | Log-regression slope over last 26 weeks |
| `log_r_squared_26w` | R² of 26-week log regression |
| `log_slope_52w` | Log-regression slope over last 52 weeks |
| `log_r_squared_52w` | R² of 52-week log regression |
| **Volatility indicators (max swings)** | |
| `max_jump_pct_1w` | Maximum 1-week percentage increase |
| `max_drop_pct_1w` | Maximum 1-week percentage decrease |
| `max_jump_pct_2w` | Maximum 2-week percentage increase |
| `max_drop_pct_2w` | Maximum 2-week percentage decrease |
| `max_jump_pct_4w` | Maximum 4-week percentage increase |
| `max_drop_pct_4w` | Maximum 4-week percentage decrease |
| **Volatility indicators (statistical)** | |
| `return_std_52w` | Standard deviation of weekly returns over 52 weeks (typical weekly variability) |
| `downside_std_52w` | Standard deviation of negative weekly returns only over 52 weeks (downside risk) |
| **Stability indicators (drawdown)** | |
| `max_drawdown_pct_4w` | Maximum peak-to-trough drawdown over last 4 weeks (positive %) |
| `max_drawdown_pct_13w` | Maximum peak-to-trough drawdown over last 13 weeks (positive %) |
| `max_drawdown_pct_26w` | Maximum peak-to-trough drawdown over last 26 weeks (positive %) |
| `max_drawdown_pct_52w` | Maximum peak-to-trough drawdown over last 52 weeks (e.g. 18.5 = fell 18.5% from peak) |
| **Stability indicators (% up-weeks)** | |
| `pct_weeks_positive_4w` | Fraction of up-weeks over last 4 weeks (0.0--1.0) |
| `pct_weeks_positive_13w` | Fraction of up-weeks over last 13 weeks (0.0--1.0) |
| `pct_weeks_positive_26w` | Fraction of up-weeks over last 26 weeks (0.0--1.0) |
| `pct_weeks_positive_52w` | Fraction of up-weeks over last 52 weeks (0.0--1.0) |
| `total_weeks` | Total number of weeks analyzed |
| **Momentum shape** | |
| `acceleration_pct_13w` | Momentum acceleration over 13 weeks (positive = speeding up) |
| `from_high_pct_4w` | Distance from 4-week high in % (always <= 0, closer to 0 = near recent high) |
| **Moving average structure** | |
| `price_vs_ma20_pct` | Current price vs 20-day SMA in % (positive = above MA) |
| `price_vs_ma50_pct` | Current price vs 50-day SMA in % |
| `price_vs_ma100_pct` | Current price vs 100-day SMA in % |
| `price_vs_ma200_pct` | Current price vs 200-day SMA in % |
| `ma50_vs_ma200_pct` | 50-day SMA vs 200-day SMA in % (positive = golden-cross territory) |

Example trend-gated rule:
```
price_vs_ma200_pct > 0 AND ma50_vs_ma200_pct > 0 AND change_pct_13w > 10
```

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
