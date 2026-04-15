"""Tool definitions and executors for the AI strategy agent."""

import json
import logging
from datetime import datetime


from stockidea.datasource.database import conn
from stockidea.rule_engine import compile_rule
from stockidea.backtest.backtester import Backtester
from stockidea.types import StockIndex, StockIndicators, BacktestResult

logger = logging.getLogger(__name__)


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
                "Example: 'change_13w_pct > 10 AND max_drop_2w_pct < 15 AND linear_r_squared > 0.7'"
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
    },
    "required": ["rule", "date_start", "date_end"],
}

_BACKTEST_DESC = (
    "Run a backtest backtest with the given rule and parameters. "
    "Returns backtest scores (Sharpe, Sortino, Calmar, win rate, etc.) and summary. "
    "Use this to test a strategy rule and evaluate its performance."
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

# Anthropic format
ANTHROPIC_TOOLS = [
    {
        "name": "run_backtest",
        "description": _BACKTEST_DESC,
        "input_schema": _BACKTEST_PARAMS,
    },
    {
        "name": "list_indicator_fields",
        "description": _LIST_INDICATORS_DESC,
        "input_schema": _LIST_INDICATORS_PARAMS,
    },
]

# OpenAI format
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": _BACKTEST_DESC,
            "parameters": _BACKTEST_PARAMS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_indicator_fields",
            "description": _LIST_INDICATORS_DESC,
            "parameters": _LIST_INDICATORS_PARAMS,
        },
    },
]


# =============================================================================
# Tool field metadata
# =============================================================================

INDICATOR_FIELD_DESCRIPTIONS: dict[str, str] = {
    "symbol": "Stock ticker symbol (string, not usable in rules)",
    "date": "Indicator computation date (not usable in rules)",
    "total_weeks": "Number of weeks of data available (integer)",
    # Trend metrics
    "linear_slope_pct": "Weekly linear regression slope as % of starting price. Positive = uptrend. Typical range: -2 to +3",
    "linear_r_squared": "R² of linear regression (0-1). Higher = more consistent trend. >0.7 is strong",
    "log_slope": "Log-scale regression slope. Positive = uptrend",
    "log_r_squared": "R² of log regression (0-1)",
    # Return metrics
    "change_1w_pct": "1-week price change in %. Typical range: -10 to +10",
    "change_2w_pct": "2-week price change in %. Typical range: -15 to +15",
    "change_4w_pct": "4-week price change in %. Typical range: -20 to +20",
    "change_13w_pct": "13-week (quarterly) price change in %. Typical range: -30 to +40",
    "change_26w_pct": "26-week (half-year) price change in %. Typical range: -40 to +60",
    "change_1y_pct": "52-week (yearly) price change in %. Typical range: -50 to +100",
    # Volatility metrics
    "max_jump_1w_pct": "Largest 1-week positive move in %. Always positive. Typical: 2-15",
    "max_drop_1w_pct": "Largest 1-week negative move in % (stored as positive). Typical: 2-15",
    "max_jump_2w_pct": "Largest 2-week positive move in %. Typical: 3-20",
    "max_drop_2w_pct": "Largest 2-week negative move in % (stored as positive). Typical: 3-20",
    "max_jump_4w_pct": "Largest 4-week positive move in %. Typical: 5-25",
    "max_drop_4w_pct": "Largest 4-week negative move in % (stored as positive). Typical: 5-25",
    # Volatility metrics (statistical)
    "weekly_return_std": "Standard deviation of weekly % returns. Measures typical weekly variability. Typical: 1-8. Lower = smoother",
    "downside_std": "Standard deviation of negative weekly returns only. Measures downside risk. Typical: 1-6. Lower = less downside volatility",
    # Stability metrics
    "max_drawdown_pct": "Maximum peak-to-trough decline in % (stored as positive). Typical: 5-40. Lower is better",
    "pct_weeks_positive": "Fraction of weeks with positive return (0.0-1.0). >0.55 is good",
    "slope_13w_pct": "Linear slope over last 13 weeks as % of starting price per week",
    "r_squared_13w": "R² of 13-week regression (0-1)",
    "r_squared_4w": "R² of 4-week regression (0-1). Short-term trend consistency. >0.7 means clean recent trend",
    "slope_26w_pct": "Linear slope over last 26 weeks as % of starting price per week",
    "r_squared_26w": "R² of 26-week regression (0-1)",
    # Momentum shape
    "acceleration_13w": "Momentum acceleration over 13 weeks (recent-half slope minus earlier-half slope, as % per week). Positive = speeding up, negative = slowing down. Typical: -1 to +1",
    "pct_from_4w_high": "Distance from 4-week high in %. Always <= 0. Typical: -10 to 0. Closer to 0 = near recent high",
}


# =============================================================================
# Tool executors
# =============================================================================


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    if tool_name == "run_backtest":
        return await _run_backtest(tool_input)
    elif tool_name == "list_indicator_fields":
        return _list_indicator_fields()
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def _run_backtest(params: dict) -> str:
    """Execute a backtest and return scores as JSON."""
    rule_str = params["rule"]
    date_start_str = params["date_start"]
    date_end_str = params["date_end"]
    max_stocks = params.get("max_stocks", 3)
    rebalance_interval_weeks = params.get("rebalance_interval_weeks", 2)
    index_str = params.get("index", "SP500")

    try:
        rule_func = compile_rule(rule_str)
    except Exception as e:
        return json.dumps({"error": f"Invalid rule expression: {e}"})

    try:
        date_start = datetime.strptime(date_start_str, "%Y-%m-%d")
        date_end = datetime.strptime(date_end_str, "%Y-%m-%d")
    except ValueError:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    stock_index = StockIndex(index_str)

    try:
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
            )
            result: BacktestResult = await backtester.backtest()
    except Exception as e:
        logger.exception(f"Backtest failed: {e}")
        return json.dumps({"error": f"Backtest failed: {e}"})

    # Return a concise summary with scores
    summary = {
        "rule": rule_str,
        "date_start": date_start_str,
        "date_end": date_end_str,
        "max_stocks": max_stocks,
        "rebalance_interval_weeks": rebalance_interval_weeks,
        "index": index_str,
        "initial_balance": result.initial_balance,
        "final_balance": round(result.final_balance, 2),
        "profit_pct": round(result.profit_pct * 100, 2),
        "baseline_profit_pct": round(result.baseline_profit_pct * 100, 2),
        "num_rebalances": len(result.rebalance_history),
    }
    if result.scores:
        summary["scores"] = result.scores.model_dump()

    return json.dumps(summary)


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
