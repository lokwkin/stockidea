"""Tool definitions and executors for the AI strategy agent."""

import json
import logging
from datetime import datetime


from stockidea.datasource.database import conn
from stockidea.rule_engine import compile_rule
from stockidea.simulation.simulator import Simulator
from stockidea.types import StockIndex, StockMetrics, SimulationResult

logger = logging.getLogger(__name__)


# =============================================================================
# Tool schemas — shared parameters, provider-specific wrappers
# =============================================================================

_SIMULATION_PARAMS = {
    "type": "object",
    "properties": {
        "rule": {
            "type": "string",
            "description": (
                "Filter rule expression using StockMetrics fields. "
                "Supports AND/OR operators and comparisons. "
                "Example: 'change_13w_pct > 10 AND max_drop_2w_pct < 15 AND linear_r_squared > 0.7'"
            ),
        },
        "date_start": {
            "type": "string",
            "description": "Simulation start date in YYYY-MM-DD format",
        },
        "date_end": {
            "type": "string",
            "description": "Simulation end date in YYYY-MM-DD format",
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

_SIMULATION_DESC = (
    "Run a backtest simulation with the given rule and parameters. "
    "Returns simulation scores (Sharpe, Sortino, Calmar, win rate, etc.) and summary. "
    "Use this to test a strategy rule and evaluate its performance."
)

_LIST_METRICS_DESC = (
    "List all available StockMetrics fields that can be used in rule expressions. "
    "Returns field names with their descriptions and typical value ranges. "
    "Call this first to understand what metrics are available for building rules."
)

_LIST_METRICS_PARAMS = {
    "type": "object",
    "properties": {},
    "required": [],
}

# Anthropic format
ANTHROPIC_TOOLS = [
    {
        "name": "run_simulation",
        "description": _SIMULATION_DESC,
        "input_schema": _SIMULATION_PARAMS,
    },
    {
        "name": "list_metric_fields",
        "description": _LIST_METRICS_DESC,
        "input_schema": _LIST_METRICS_PARAMS,
    },
]

# OpenAI format
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_simulation",
            "description": _SIMULATION_DESC,
            "parameters": _SIMULATION_PARAMS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_metric_fields",
            "description": _LIST_METRICS_DESC,
            "parameters": _LIST_METRICS_PARAMS,
        },
    },
]


# =============================================================================
# Tool field metadata
# =============================================================================

METRIC_FIELD_DESCRIPTIONS: dict[str, str] = {
    "symbol": "Stock ticker symbol (string, not usable in rules)",
    "date": "Metrics computation date (not usable in rules)",
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
    # Stability metrics
    "max_drawdown_pct": "Maximum peak-to-trough decline in % (stored as positive). Typical: 5-40. Lower is better",
    "pct_weeks_positive": "Fraction of weeks with positive return (0.0-1.0). >0.55 is good",
    "slope_13w_pct": "Linear slope over last 13 weeks as % of starting price per week",
    "r_squared_13w": "R² of 13-week regression (0-1)",
    "slope_26w_pct": "Linear slope over last 26 weeks as % of starting price per week",
    "r_squared_26w": "R² of 26-week regression (0-1)",
}


# =============================================================================
# Tool executors
# =============================================================================


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    if tool_name == "run_simulation":
        return await _run_simulation(tool_input)
    elif tool_name == "list_metric_fields":
        return _list_metric_fields()
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def _run_simulation(params: dict) -> str:
    """Execute a simulation and return scores as JSON."""
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
            simulator = Simulator(
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
            result: SimulationResult = await simulator.simulate()
    except Exception as e:
        logger.exception(f"Simulation failed: {e}")
        return json.dumps({"error": f"Simulation failed: {e}"})

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


def _list_metric_fields() -> str:
    """Return available StockMetrics fields with descriptions."""
    fields = []
    for field_name, field_info in StockMetrics.model_fields.items():
        desc = METRIC_FIELD_DESCRIPTIONS.get(field_name, "")
        fields.append(
            {
                "name": field_name,
                "type": getattr(field_info.annotation, "__name__", None)
                or str(field_info.annotation),
                "description": desc,
            }
        )
    return json.dumps({"fields": fields})
