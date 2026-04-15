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

## Common Commands

```bash
# Backend — Data fetching
uv run python -m stockidea.cli fetch-data                    # refresh ALL data (constituents + index + stock prices) for SP500 & NASDAQ
uv run python -m stockidea.cli fetch-constituents --index SP500
uv run python -m stockidea.cli fetch-index --index SP500
uv run python -m stockidea.cli fetch-prices --index SP500

# Backend — Analysis & Simulation
uv run python -m stockidea.cli analyze -d 2026-01-20
uv run python -m stockidea.cli pick -r 'change_13w_pct > 10 AND max_drop_2w_pct < 15'
uv run python -m stockidea.cli simulate --date-start=2022-01-01 --date-end=2026-01-20 --rule='change_13w_pct > 10'

# Backend — AI Agent
uv run python -m stockidea.cli agent -i "I want a momentum strategy that avoids big drops"
uv run python -m stockidea.cli agent -i "momentum strategy" -m gpt-4o   # use OpenAI instead of Claude

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

1. User provides a high-level direction (e.g. "I want a strong momentum strategy")
2. An LLM agent translates that into a concrete rule + simulation config
3. The agent runs backtests iteratively, reads results, adjusts rule/params, and repeats
4. The system surfaces the best-performing strategy with guardrails against overfitting

The existing backtester + rule engine is the foundation — the AI agent layer sits on top of it, using `POST /simulate` as its core tool.

### Current gaps toward this vision
- **No out-of-sample split** — train/test separation needed to prevent overfitting
- **No strategy versioning** — no concept of a named strategy with iteration history and cross-run comparison
- **Limited signal coverage** — current indicators cover momentum/trend only; broader strategy types (volatility, fundamentals) need more indicator fields

## Architecture

### Backend (`src/stockidea/`)

FastAPI app with an **in-process async worker loop** for long-running simulations:

- `constants.py` — All environment variables loaded via `dotenv` in one place (FMP keys, DB credentials, LLM API keys)
- `config.py` — Logging setup only (FlushHandler, setup_logging)
- `api.py` — All HTTP routes + `lifespan` context that starts the background worker and auto-refreshes data on startup
- `types.py` — All Pydantic v2 models shared across the app (including `SimulationScores`); `StockIndex` enum covers SP500 and NASDAQ only
- `rule_engine.py` — Compiles user-written filter strings (e.g. `change_13w_pct > 10 AND max_drop_2w_pct < 15`) into callables using `simpleeval`
- `datasource/` — FMP API client, market data abstraction, SQLAlchemy async models/queries/connection
  - `datasource/service.py` — High-level fetch orchestration with `refresh_all()` for startup; `SUPPORTED_INDEXES` constant
  - `datasource/fmp.py` — FMP API client; API key checked at call time (not import time)
  - `datasource/database/` — SQLAlchemy models (`models.py`), queries (`queries.py`), connection pool (`conn.py`)
- `indicators/` — Pre-computed stock indicators for strategy evaluation
  - `indicators/service.py` — Fetches/computes indicator batches, applies rules
  - `indicators/calculator.py` — Aggregates daily prices to Friday-close weekly series, computes all indicator fields, ranks by stability score
- `simulation/` — Core backtest engine
  - `simulation/simulator.py` — Iterates rebalance dates, calls `pick_stocks()`, simulates trades
  - `simulation/scoring.py` — Computes objective scores (Sharpe, Sortino, Calmar, win rate, drawdown) from simulation results
- `agent/` — AI strategy agent supporting both Anthropic Claude and OpenAI GPT
  - `agent/agent.py` — Agentic loop with auto-detection of provider from model name; streams SSE events
  - `agent/tools.py` — Tool definitions and executors (run_simulation, list_indicator_fields); dual format for Anthropic/OpenAI

**Data storage**: All data lives in PostgreSQL — stock prices, index prices, constituent change history, indicators, simulations. No file-based caching. Freshness is checked via metadata tables with 1-day TTL.

**Job queue flow**: `POST /simulate` saves a "pending" `simulation_job` row and returns a `job_id`. The worker loop (`_worker_loop` in `api.py`) polls the DB, claims pending jobs, runs `Simulator.simulate()`, and writes the result back. No external queue.

**Database models** use a `DB{Entity}` naming prefix (`DBSimulation`, `DBSimulationJob`, etc.). Tables are created on startup — there are no migration files.

### Frontend (`frontend/src/`)

React 19 + TypeScript SPA with React Router v7:

- Views (`*View.tsx`) are full-page route components; reusable pieces live in `components/`
- `App.tsx` owns routing and the `Sidebar`, which polls `GET /api/jobs` adaptively (3 s when a job is active, 15 s otherwise)
- `AgentView.tsx` — Chat-like UI with SSE streaming for the AI agent
- API calls always use relative `/api/...` paths — Vite proxies them to the backend in dev
- No external state management; all state is local React hooks

### Key Patterns

**Async-first Python**: all I/O uses `async def` + `asyncpg`/`httpx`; DB sessions via `async with conn.get_db_session() as db_session:`.

**Constituent lookups require db_session**: `datasource_service.get_constituent_at(db_session, index, target_date)` — always called within a `get_db_session()` context.

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
