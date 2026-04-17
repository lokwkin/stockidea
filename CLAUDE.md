# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

```bash
cp .env.example .env   # fill in FMP_API_KEY, Postgres credentials, and optionally ANTHROPIC_API_KEY / OPENAI_API_KEY
docker-compose up -d   # starts PostgreSQL 16 + backend (port 8000)
cd frontend && npm run dev  # frontend dev server (port 5173, proxies /api/* to backend)
```

Backend only (without Docker):
```bash
uv run uvicorn stockidea.api:app --reload
```

Database migrations (after model changes):
```bash
uv run alembic upgrade head
```

## Common Commands

```bash
# Backend — Data fetching
uv run python -m stockidea.cli fetch-data                    # refresh ALL data (constituents + index + stock prices) for SP500 & NASDAQ
uv run python -m stockidea.cli fetch-constituents --index SP500
uv run python -m stockidea.cli fetch-index --index SP500
uv run python -m stockidea.cli fetch-prices --index SP500

# Backend — Analysis & Backtest
uv run python -m stockidea.cli compute -d 2026-01-20
uv run python -m stockidea.cli pick -r 'change_pct_13w > 10 AND max_drop_pct_2w < 15'
uv run python -m stockidea.cli backtest --date-start=2022-01-01 --date-end=2026-01-20 --rule='change_pct_13w > 10'

# Backend — AI Agent (creates a strategy in DB, runs 5-10 backtest iterations)
uv run python -m stockidea.cli agent -i "I want a momentum strategy that avoids big drops"
uv run python -m stockidea.cli agent -i "momentum strategy" -m gpt-5.4   # use OpenAI instead of Claude

# Type checking (run after every code change)
uv run mypy src/stockidea
uv run ruff format src/stockidea
uv run ruff check src/stockidea --fix

# Frontend
cd frontend && npm run build
cd frontend && npm run lint
```

There are no automated tests.

## Product Vision

The ultimate goal is an **AI-driven strategy design and optimization platform**:

1. User creates a **Strategy Idea** with a natural language instruction
2. An LLM agent translates that into concrete rules and runs 5-10 backtest iterations autonomously
3. The user can send **follow-up instructions** (multi-turn conversation) to refine the strategy
4. The agent resumes with full conversation context for each follow-up round
5. All backtests are linked to the strategy for comparison and iteration tracking

### Current gaps toward this vision
- **No out-of-sample split** — train/test separation needed to prevent overfitting
- **Limited signal coverage** — current indicators cover momentum/trend only; broader strategy types (volatility, fundamentals) need more indicator fields

## Architecture

### Backend (`src/stockidea/`)

FastAPI app where backtests execute synchronously inside the request that triggers them. CLI and API routes are distributed across component modules — the root `api.py` and `cli.py` are thin assemblers that wire components together.

**Shared modules:**
- `api.py` — Assembles FastAPI app: lifespan (startup data refresh), CORS, includes component routers
- `cli.py` — Assembles Click CLI: flattens component subcommands into top-level commands
- `constants.py` — All environment variables loaded via `dotenv` in one place (FMP keys, DB credentials, LLM API keys)
- `config.py` — Logging setup only (FlushHandler, setup_logging)
- `types.py` — All Pydantic v2 models shared across the app (including `BacktestScores`, `StrategyCreate`, `StrategySummary`, `StrategyDetail`); `StockIndex` enum covers SP500 and NASDAQ only
- `rule_engine.py` — Compiles user-written filter strings (e.g. `change_pct_13w > 10 AND max_drop_pct_2w < 15`) into callables using `simpleeval`

**Component modules** — each has `service.py` (business logic), `router.py` (API routes), and `cli.py` (CLI commands):

- `datasource/` — FMP API client, market data abstraction, SQLAlchemy async models/queries/connection
  - `router.py` — `GET /snp500`, `GET /stocks/{symbol}/profile`, `GET /stocks/{symbol}/prices`
  - `cli.py` — `fetch-data`, `fetch-prices`, `fetch-index`, `fetch-constituents`
  - `service.py` — High-level fetch orchestration with `refresh_all()` for startup; `SUPPORTED_INDEXES` constant
  - `fmp.py` — FMP API client; API key checked at call time (not import time)
  - `database/` — SQLAlchemy models (`models.py`), queries (`queries.py`), connection pool (`conn.py`)
- `indicators/` — Pre-computed stock indicators for strategy evaluation
  - `router.py` — `GET /indicators`, `GET /indicators/{date}/`, `GET /indicators/symbol/{symbol}/latest`, `GET /indicators/symbol/{symbol}/{date}`
  - `cli.py` — `compute`, `pick`
  - `service.py` — Fetches/computes indicator batches, applies rules
  - `calculator.py` — Aggregates daily prices to Friday-close weekly series, computes all indicator fields, ranks by stability score
- `backtest/` — Core backtest engine
  - `router.py` — `POST /backtest`, `GET /backtests`, `GET /backtests/{id}` (synchronous — the POST runs the full backtest before returning)
  - `cli.py` — `backtest`
  - `backtester.py` — Iterates rebalance dates, calls `pick_stocks()`, executes trades
  - `scoring.py` — Computes objective scores (Sharpe, Sortino, Calmar, win rate, drawdown) from backtest results
- `agent/` — AI strategy agent supporting both Anthropic Claude and OpenAI GPT
  - `router.py` — `GET/POST/DELETE /strategies`, `GET /strategies/{id}/notes`, `POST /strategies/{id}/messages`
  - `cli.py` — `agent`
  - `agent.py` — Multi-turn agentic loop with auto-detection of provider from model name; streams SSE events; persists LLM message history for conversation continuation
  - `tools.py` — Tool definitions and executors (run_backtest, list_indicator_fields, preview_filter, write_strategy_notes, read_strategy_notes, lookup_stock); dual format for Anthropic/OpenAI; `strategy_id` is required for all tool executions

**Data storage**: All data lives in PostgreSQL — stock prices, index prices, constituent change history, indicators, backtests, strategies, strategy messages. Managed via Alembic migrations. Freshness is checked via metadata tables with 1-day TTL.

**Backtest flow**: `POST /backtest` runs `Backtester.backtest()` synchronously inside the request handler, persists the result via `queries.save_backtest_result()`, and returns the full `BacktestResult`. There is no job queue or background worker.

**Strategy flow**: `POST /strategies` creates a `DBStrategy`, saves the user message as `DBStrategyMessage`, runs the agent (SSE stream), and persists agent events + LLM history on completion. `POST /strategies/{id}/messages` loads prior LLM history and resumes the agent for multi-turn conversation.

**Database models** use a `DB{Entity}` naming prefix (`DBBacktest`, `DBStrategy`, `DBStrategyMessage`, etc.).

### Frontend (`frontend/src/`)

React 19 + TypeScript SPA with React Router v7:

- Views (`*View.tsx`) are full-page route components; reusable pieces live in `components/`
- `App.tsx` owns routing and the `Sidebar` with sections for Strategies (status indicators), Create Backtest, Backtests, Indicators, and Stocks
- `CreateStrategyView.tsx` — Strategy creation form (instruction, model selector, date range)
- `CreateBacktestView.tsx` — Manual backtest form (rule, ranking expression, date range, index); sends naive midnight datetimes to match CLI behavior
- `StrategyView.tsx` — Multi-turn chat UI with SSE streaming, backtest comparison table, follow-up input
- `StockChartView.tsx` — Per-symbol page (`/chart/:symbol`) showing FMP company profile + peers above the price/volume charts
- API calls always use relative `/api/...` paths — Vite proxies them to the backend in dev
- No external state management; all state is local React hooks

### Key Patterns

**Async-first Python**: all I/O uses `async def` + `asyncpg`/`httpx`; DB sessions via `async with conn.get_db_session() as db_session:`.

**Constituent lookups require db_session**: `datasource_service.get_constituent_at(db_session, index, target_date)` — always called within a `get_db_session()` context.

**Multi-turn agent conversation**: LLM message history is serialized and persisted on `DBStrategy.llm_history_json`. On follow-up messages, the history is deserialized and passed to `run_agent_stream(history=...)` so the agent continues with full context. Anthropic messages require special serialization (`_serialize_anthropic_messages`) due to content block objects.

**React fetch with cancellation**:
```ts
let cancelled = false
useEffect(() => {
  fetch(url).then(res => { if (!cancelled) setState(res) })
  return () => { cancelled = true }
}, [dep])
```

**Polling**: recursive `setTimeout` (not `setInterval`), interval varies by state.

**Memoization**: `memo()` on table components, `useMemo` for sorted/filtered data, `useCallback` for stable refs.
