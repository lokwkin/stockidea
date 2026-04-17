"""Tool definitions and executors for the AI strategy agent."""

import json
import logging
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

from stockidea.datasource.database import conn
from stockidea.datasource import service as datasource_service
from stockidea.indicators import service as indicators_service
from stockidea.rule_engine import (
    DEFAULT_RANKING,
    compile_ranking,
    compile_rule,
    extract_involved_keys,
)
from stockidea.backtest.backtester import Backtester
from stockidea.types import StockIndex, StockIndicators, BacktestResult

logger = logging.getLogger(__name__)

STRATEGIES_DIR = (
    Path(os.path.dirname(__file__)).parent.parent.parent / "data" / "strategies"
)


# =============================================================================
# Tool schemas — shared parameters, provider-specific wrappers
# =============================================================================

_BACKTEST_PARAMS = {
    "type": "object",
    "properties": {
        "rule": {
            "type": "string",
            "description": (
                "Filter rule expression using StockIndicators fields. "
                "Supports AND/OR operators and comparisons. "
                "Example: 'change_pct_13w > 10 AND max_drop_pct_2w < 15 AND r_squared_52w > 0.7'"
            ),
        },
        "date_start": {
            "type": "string",
            "description": "Backtest start date in YYYY-MM-DD format",
        },
        "date_end": {
            "type": "string",
            "description": "Backtest end date in YYYY-MM-DD format",
        },
        "max_stocks": {
            "type": "integer",
            "description": "Maximum number of stocks to hold at once (default: 3)",
            "default": 3,
        },
        "rebalance_interval_weeks": {
            "type": "integer",
            "description": "Weeks between portfolio rebalances (default: 2)",
            "default": 2,
        },
        "index": {
            "type": "string",
            "enum": ["SP500", "NASDAQ"],
            "description": "Stock index universe (default: SP500)",
            "default": "SP500",
        },
        "ranking": {
            "type": "string",
            "description": (
                "Ranking expression to sort filtered stocks. Uses StockIndicators fields "
                "and returns a numeric score (higher = better). "
                f"Default: '{DEFAULT_RANKING}'. "
                "Examples: 'slope_pct_52w * r_squared_52w', "
                "'change_pct_26w / max_drawdown_pct_52w', "
                "'slope_pct_13w * r_squared_13w + 0.5 * change_pct_4w'"
            ),
        },
    },
    "required": ["rule", "date_start", "date_end"],
}

_BACKTEST_DESC = (
    "Run a backtest with the given rule and parameters. "
    "Returns scores (Sharpe, Sortino, Calmar, win rate, etc.), summary, "
    "and diagnostics (worst/best periods, stock selection stats). "
    "Use this to test a strategy rule and evaluate its performance."
)

_PREVIEW_FILTER_PARAMS = {
    "type": "object",
    "properties": {
        "rule": {
            "type": "string",
            "description": "Filter rule expression using StockIndicators fields.",
        },
        "date": {
            "type": "string",
            "description": "Date to evaluate the filter on, in YYYY-MM-DD format.",
        },
        "index": {
            "type": "string",
            "enum": ["SP500", "NASDAQ"],
            "description": "Stock index universe (default: SP500)",
            "default": "SP500",
        },
        "ranking": {
            "type": "string",
            "description": (
                "Ranking expression to sort filtered stocks (higher = better). "
                f"Default: '{DEFAULT_RANKING}'"
            ),
        },
    },
    "required": ["rule", "date"],
}

_PREVIEW_FILTER_DESC = (
    "Preview how many stocks pass a filter rule at a given date WITHOUT running a full backtest. "
    "Returns the count of matching stocks and a sample of top 5 with their indicator values. "
    "Use this to quickly calibrate rule thresholds before committing to a full backtest."
)

_LIST_INDICATORS_DESC = (
    "List all available StockIndicators fields that can be used in rule expressions. "
    "Returns field names with their descriptions and typical value ranges. "
    "Call this first to understand what indicators are available for building rules."
)

_LIST_INDICATORS_PARAMS = {
    "type": "object",
    "properties": {},
    "required": [],
}

_WRITE_NOTES_PARAMS = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "Markdown content — your reasoning, iteration history, and observations",
        },
    },
    "required": ["content"],
}

_WRITE_NOTES_DESC = (
    "Save strategy notes as a markdown file. Use this to persist your reasoning, "
    "iteration history, what worked and what didn't, and your current best approach. "
    "Overwrites any existing notes for this strategy. Call this after every backtest "
    "to build up a running log."
)

_READ_NOTES_PARAMS = {
    "type": "object",
    "properties": {},
    "required": [],
}

_READ_NOTES_DESC = (
    "Read back the strategy notes for the current strategy. "
    "Returns the markdown content previously saved with write_strategy_notes."
)

_LOOKUP_STOCK_PARAMS = {
    "type": "object",
    "properties": {
        "symbols": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of stock ticker symbols to look up (e.g. ['AAPL', 'NVDA'])",
        },
        "date": {
            "type": "string",
            "description": "Date to retrieve indicators for, in YYYY-MM-DD format.",
        },
    },
    "required": ["symbols", "date"],
}

_LOOKUP_STOCK_DESC = (
    "Look up indicator data for specific stock(s) at a given date. "
    "Returns all computed indicator values for each symbol. "
    "Use this to inspect individual stocks — e.g. to understand why a stock was or wasn't selected, "
    "or to see the actual indicator values for stocks of interest."
)


def _tool_anthropic(name: str, description: str, params: dict) -> dict:
    return {"name": name, "description": description, "input_schema": params}


def _tool_openai(name: str, description: str, params: dict) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": params},
    }


# Anthropic format
ANTHROPIC_TOOLS = [
    _tool_anthropic("run_backtest", _BACKTEST_DESC, _BACKTEST_PARAMS),
    _tool_anthropic("preview_filter", _PREVIEW_FILTER_DESC, _PREVIEW_FILTER_PARAMS),
    _tool_anthropic(
        "list_indicator_fields", _LIST_INDICATORS_DESC, _LIST_INDICATORS_PARAMS
    ),
    _tool_anthropic("write_strategy_notes", _WRITE_NOTES_DESC, _WRITE_NOTES_PARAMS),
    _tool_anthropic("read_strategy_notes", _READ_NOTES_DESC, _READ_NOTES_PARAMS),
    _tool_anthropic("lookup_stock", _LOOKUP_STOCK_DESC, _LOOKUP_STOCK_PARAMS),
]

# OpenAI format
OPENAI_TOOLS = [
    _tool_openai("run_backtest", _BACKTEST_DESC, _BACKTEST_PARAMS),
    _tool_openai("preview_filter", _PREVIEW_FILTER_DESC, _PREVIEW_FILTER_PARAMS),
    _tool_openai(
        "list_indicator_fields", _LIST_INDICATORS_DESC, _LIST_INDICATORS_PARAMS
    ),
    _tool_openai("write_strategy_notes", _WRITE_NOTES_DESC, _WRITE_NOTES_PARAMS),
    _tool_openai("read_strategy_notes", _READ_NOTES_DESC, _READ_NOTES_PARAMS),
    _tool_openai("lookup_stock", _LOOKUP_STOCK_DESC, _LOOKUP_STOCK_PARAMS),
]


# =============================================================================
# Tool field metadata
# =============================================================================

INDICATOR_FIELD_DESCRIPTIONS: dict[str, str] = {
    "symbol": "Stock ticker symbol (string, not usable in rules)",
    "date": "Indicator computation date (not usable in rules)",
    "total_weeks": "Number of weeks of data available (integer)",
    # Linear regression slope (% per week)
    "slope_pct_13w": "Linear slope over last 13 weeks as % of starting price per week",
    "slope_pct_26w": "Linear slope over last 26 weeks as % of starting price per week",
    "slope_pct_52w": "Linear slope over the full 52-week series as % of starting price per week. Positive = uptrend. Typical range: -2 to +3",
    # Linear regression R²
    "r_squared_4w": "R² of 4-week regression (0-1). Short-term trend consistency. >0.7 means clean recent trend",
    "r_squared_13w": "R² of 13-week regression (0-1)",
    "r_squared_26w": "R² of 26-week regression (0-1)",
    "r_squared_52w": "R² of full-series linear regression (0-1). Higher = more consistent trend. >0.7 is strong",
    # Log regression slope and R²
    "log_slope_13w": "Log-scale regression slope over last 13 weeks. Positive = uptrend",
    "log_r_squared_13w": "R² of 13-week log regression (0-1)",
    "log_slope_26w": "Log-scale regression slope over last 26 weeks. Positive = uptrend",
    "log_r_squared_26w": "R² of 26-week log regression (0-1)",
    "log_slope_52w": "Log-scale regression slope over full series. Positive = uptrend",
    "log_r_squared_52w": "R² of full-series log regression (0-1)",
    # Point-to-point change
    "change_pct_1w": "1-week price change in %. Typical range: -10 to +10",
    "change_pct_2w": "2-week price change in %. Typical range: -15 to +15",
    "change_pct_4w": "4-week price change in %. Typical range: -20 to +20",
    "change_pct_13w": "13-week (quarterly) price change in %. Typical range: -30 to +40",
    "change_pct_26w": "26-week (half-year) price change in %. Typical range: -40 to +60",
    "change_pct_52w": "52-week (yearly) price change in %. Typical range: -50 to +100",
    # Max single-period swing
    "max_jump_pct_1w": "Largest 1-week positive move in %. Always positive. Typical: 2-15",
    "max_drop_pct_1w": "Largest 1-week negative move in % (stored as positive). Typical: 2-15",
    "max_jump_pct_2w": "Largest 2-week positive move in %. Typical: 3-20",
    "max_drop_pct_2w": "Largest 2-week negative move in % (stored as positive). Typical: 3-20",
    "max_jump_pct_4w": "Largest 4-week positive move in %. Typical: 5-25",
    "max_drop_pct_4w": "Largest 4-week negative move in % (stored as positive). Typical: 5-25",
    # Weekly return std-dev
    "return_std_52w": "Standard deviation of weekly % returns over full series. Measures typical weekly variability. Typical: 1-8. Lower = smoother",
    "downside_std_52w": "Standard deviation of negative weekly returns only over full series. Measures downside risk. Typical: 1-6. Lower = less downside volatility",
    # Max drawdown per window
    "max_drawdown_pct_4w": "Maximum peak-to-trough decline over last 4 weeks (positive %)",
    "max_drawdown_pct_13w": "Maximum peak-to-trough decline over last 13 weeks (positive %)",
    "max_drawdown_pct_26w": "Maximum peak-to-trough decline over last 26 weeks (positive %)",
    "max_drawdown_pct_52w": "Maximum peak-to-trough decline over the full series (positive %). Typical: 5-40. Lower is better",
    # Fraction of up-weeks per window
    "pct_weeks_positive_4w": "Fraction of weeks with positive return over last 4 weeks (0.0-1.0)",
    "pct_weeks_positive_13w": "Fraction of weeks with positive return over last 13 weeks (0.0-1.0)",
    "pct_weeks_positive_26w": "Fraction of weeks with positive return over last 26 weeks (0.0-1.0)",
    "pct_weeks_positive_52w": "Fraction of weeks with positive return over full series (0.0-1.0). >0.55 is good",
    # Momentum shape
    "acceleration_pct_13w": "Momentum acceleration over 13 weeks (recent-half slope minus earlier-half slope, as % per week). Positive = speeding up, negative = slowing down. Typical: -1 to +1",
    "from_high_pct_4w": "Distance from 4-week high in %. Always <= 0. Typical: -10 to 0. Closer to 0 = near recent high",
}

# Fields always included in preview_filter sample output
_ALWAYS_INCLUDE_FIELDS = {
    "symbol",
    "change_pct_13w",
    "r_squared_52w",
    "max_drawdown_pct_52w",
}


# =============================================================================
# Tool executors
# =============================================================================


async def execute_tool(tool_name: str, tool_input: dict, strategy_id: str) -> str:
    """Execute a tool call and return the result as a JSON string."""
    if tool_name == "run_backtest":
        return await _run_backtest(tool_input, strategy_id=strategy_id)
    elif tool_name == "preview_filter":
        return await _preview_filter(tool_input)
    elif tool_name == "list_indicator_fields":
        return _list_indicator_fields()
    elif tool_name == "write_strategy_notes":
        return await _write_strategy_notes(tool_input, strategy_id=strategy_id)
    elif tool_name == "read_strategy_notes":
        return _read_strategy_notes(tool_input, strategy_id=strategy_id)
    elif tool_name == "lookup_stock":
        return await _lookup_stock(tool_input)
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _build_diagnostics(result: BacktestResult) -> dict:
    """Extract per-rebalance diagnostics and stock selection stats from backtest results."""
    history = result.backtest_rebalance

    # Per-period diagnostics
    sorted_history = sorted(history, key=lambda r: r.profit_pct)
    worst_periods = [
        {"date": r.date.strftime("%Y-%m-%d"), "profit_pct": round(r.profit_pct, 2)}
        for r in sorted_history[:3]
    ]
    best_periods = [
        {"date": r.date.strftime("%Y-%m-%d"), "profit_pct": round(r.profit_pct, 2)}
        for r in sorted_history[-3:][::-1]
    ]

    # Cash periods and average stocks per rebalance
    stocks_per_rebalance = [len(r.investments) for r in history]
    cash_periods = sum(1 for n in stocks_per_rebalance if n == 0)
    avg_stocks = (
        round(sum(stocks_per_rebalance) / len(stocks_per_rebalance), 1)
        if stocks_per_rebalance
        else 0
    )

    # Stock selection stats
    symbol_counter: Counter[str] = Counter()
    for r in history:
        for inv in r.investments:
            symbol_counter[inv.symbol] += 1

    top_held = [
        {"symbol": sym, "count": count} for sym, count in symbol_counter.most_common(5)
    ]

    return {
        "worst_periods": worst_periods,
        "best_periods": best_periods,
        "cash_periods": cash_periods,
        "avg_stocks_per_rebalance": avg_stocks,
        "total_unique_stocks": len(symbol_counter),
        "top_held_symbols": top_held,
    }


async def _run_backtest(params: dict, strategy_id: str) -> str:
    """Execute a backtest and return scores + diagnostics as JSON."""
    rule_str = params["rule"]
    date_start_str = params["date_start"]
    date_end_str = params["date_end"]
    max_stocks = params.get("max_stocks", 3)
    rebalance_interval_weeks = params.get("rebalance_interval_weeks", 2)
    index_str = params.get("index", "SP500")
    ranking_str = params.get("ranking", DEFAULT_RANKING)

    try:
        rule_func = compile_rule(rule_str)
    except Exception as e:
        return json.dumps({"error": f"Invalid rule expression: {e}"})

    try:
        ranking_func = compile_ranking(ranking_str)
    except Exception as e:
        return json.dumps({"error": f"Invalid ranking expression: {e}"})

    try:
        date_start = datetime.strptime(date_start_str, "%Y-%m-%d")
        date_end = datetime.strptime(date_end_str, "%Y-%m-%d")
    except ValueError:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    stock_index = StockIndex(index_str)

    try:
        from uuid import UUID as _UUID

        from stockidea.datasource.database.queries import (
            save_backtest_result as _save_backtest,
        )

        async with conn.get_db_session() as db_session:
            backtester = Backtester(
                db_session=db_session,
                max_stocks=max_stocks,
                rebalance_interval_weeks=rebalance_interval_weeks,
                date_start=date_start,
                date_end=date_end,
                rule_func=rule_func,
                rule_raw=rule_str,
                from_index=stock_index,
                baseline_index=StockIndex.SP500,
                ranking_func=ranking_func,
                ranking_raw=ranking_str,
            )
            result: BacktestResult = await backtester.backtest()

        # Save backtest to DB (linked to strategy if available)
        async with conn.get_db_session() as db_session:
            sid = _UUID(strategy_id) if strategy_id else None
            backtest_id = await _save_backtest(db_session, result, strategy_id=sid)
            logger.info(f"Backtest saved: {backtest_id} (strategy={strategy_id})")
    except Exception as e:
        logger.exception(f"Backtest failed: {e}")
        return json.dumps({"error": f"Backtest failed: {e}"})

    # Return a concise summary with scores and diagnostics
    summary: dict = {
        "rule": rule_str,
        "ranking": ranking_str,
        "date_start": date_start_str,
        "date_end": date_end_str,
        "max_stocks": max_stocks,
        "rebalance_interval_weeks": rebalance_interval_weeks,
        "index": index_str,
        "initial_balance": result.initial_balance,
        "final_balance": round(result.final_balance, 2),
        "profit_pct": round(result.profit_pct, 2),
        "baseline_profit_pct": round(result.baseline_profit_pct, 2),
        "num_rebalances": len(result.backtest_rebalance),
    }
    if result.scores:
        summary["scores"] = result.scores.model_dump()

    summary["diagnostics"] = _build_diagnostics(result)

    return json.dumps(summary)


async def _preview_filter(params: dict) -> str:
    """Preview how many stocks pass a filter rule at a given date."""
    rule_str = params["rule"]
    date_str = params["date"]
    index_str = params.get("index", "SP500")
    ranking_str = params.get("ranking", DEFAULT_RANKING)

    try:
        rule_func = compile_rule(rule_str)
    except Exception as e:
        return json.dumps({"error": f"Invalid rule expression: {e}"})

    try:
        ranking_func = compile_ranking(ranking_str)
    except Exception as e:
        return json.dumps({"error": f"Invalid ranking expression: {e}"})

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    stock_index = StockIndex(index_str)
    involved_keys = set(extract_involved_keys(rule_str))

    try:
        async with conn.get_db_session() as db_session:
            symbols = await datasource_service.get_constituent_at(
                db_session, stock_index, target_date.date()
            )
            total_constituents = len(symbols)

            indicators_batch = await indicators_service.get_stock_indicators_batch(
                db_session,
                symbols=symbols,
                indicators_date=target_date,
                back_period_weeks=52,
                compute_if_not_exists=True,
            )

            filtered = indicators_service.apply_rule(
                indicators_batch,
                rule_func=rule_func,
                ranking_func=ranking_func,
            )
    except Exception as e:
        logger.exception(f"Preview filter failed: {e}")
        return json.dumps({"error": f"Preview filter failed: {e}"})

    # Build sample with relevant fields only
    show_fields = _ALWAYS_INCLUDE_FIELDS | involved_keys
    sample = []
    for stock in filtered[:5]:
        entry: dict[str, object] = {}
        for field in show_fields:
            if hasattr(stock, field):
                val = getattr(stock, field)
                entry[field] = round(val, 3) if isinstance(val, float) else val
        sample.append(entry)

    return json.dumps(
        {
            "date": date_str,
            "total_constituents": total_constituents,
            "matched": len(filtered),
            "sample": sample,
        }
    )


async def _write_strategy_notes(params: dict, strategy_id: str) -> str:
    """Save strategy notes as a markdown file on the filesystem."""
    content = params["content"]

    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = STRATEGIES_DIR / f"{strategy_id}.md"
    filepath.write_text(content, encoding="utf-8")

    return json.dumps({"path": str(filepath), "status": "saved"})


def _read_strategy_notes(params: dict, strategy_id: str) -> str:
    """Read strategy notes from the filesystem."""
    # Read notes for the current strategy
    filepath = STRATEGIES_DIR / f"{strategy_id}.md"
    if not filepath.exists():
        return json.dumps({"error": "No notes found for this strategy yet."})

    content = filepath.read_text(encoding="utf-8")
    return json.dumps({"strategy_id": strategy_id, "content": content})


async def _lookup_stock(params: dict) -> str:
    """Look up indicator data for specific stocks at a given date."""
    symbols: list[str] = [s.upper() for s in params["symbols"]]
    date_str: str = params["date"]

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    try:
        async with conn.get_db_session() as db_session:
            indicators = await indicators_service.get_stock_indicators_batch(
                db_session,
                symbols=symbols,
                indicators_date=target_date,
                back_period_weeks=52,
                compute_if_not_exists=True,
            )
    except Exception as e:
        logger.exception(f"Lookup stock failed: {e}")
        return json.dumps({"error": f"Lookup stock failed: {e}"})

    results = []
    for ind in indicators:
        entry = ind.model_dump(mode="json")
        for field_name, val in entry.items():
            if isinstance(val, float):
                entry[field_name] = round(val, 4)
        results.append(entry)

    # Report symbols that weren't found
    found_symbols = {ind.symbol for ind in indicators}
    missing = [s for s in symbols if s not in found_symbols]

    return json.dumps(
        {
            "date": date_str,
            "stocks": results,
            "missing": missing,
        }
    )


def _list_indicator_fields() -> str:
    """Return available StockIndicators fields with descriptions."""
    fields = []
    for field_name, field_info in StockIndicators.model_fields.items():
        desc = INDICATOR_FIELD_DESCRIPTIONS.get(field_name, "")
        fields.append(
            {
                "name": field_name,
                "type": getattr(field_info.annotation, "__name__", None)
                or str(field_info.annotation),
                "description": desc,
            }
        )
    return json.dumps({"fields": fields})
