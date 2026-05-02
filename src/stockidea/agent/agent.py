"""AI strategy agent that translates human ideas into backtested trading rules."""

import json
import logging
from datetime import date, timedelta
from typing import Any, AsyncGenerator

from stockidea.agent.tools import ANTHROPIC_TOOLS, OPENAI_TOOLS, execute_tool
from stockidea.constants import ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def _serialize_anthropic_messages(messages: list[dict]) -> str:
    """Serialize Anthropic message history to JSON for persistence.

    Anthropic messages may contain content block objects that need special handling.
    """

    def _serialize_content(content: Any) -> Any:
        if isinstance(content, list):
            result = []
            for item in content:
                if hasattr(item, "model_dump"):
                    result.append(item.model_dump())
                elif hasattr(item, "to_dict"):
                    result.append(item.to_dict())
                elif isinstance(item, dict):
                    result.append(item)
                else:
                    # Try converting to dict via __dict__, fallback to str
                    try:
                        result.append(
                            {
                                k: v
                                for k, v in item.__dict__.items()
                                if not k.startswith("_")
                            }
                        )
                    except AttributeError:
                        result.append(str(item))
            return result
        return content

    serializable = []
    for msg in messages:
        entry = dict(msg)
        if "content" in entry:
            entry["content"] = _serialize_content(entry["content"])
        serializable.append(entry)
    return json.dumps(serializable)


SYSTEM_PROMPT = """\
You are a quantitative strategy designer. Your job is to help the user design \
stock trading strategies by writing filter rules and backtesting them.

## How it works

1. The user gives you a high-level idea (e.g. "I want a momentum strategy that avoids volatile stocks").
2. You translate that into a concrete rule expression using available StockIndicators fields.
3. You preview the filter to calibrate thresholds, then run a full backtest.
4. You analyze results including diagnostics (worst/best periods, stock selection stats) and iterate.
5. When satisfied, you present the final strategy with its performance summary.

## Rule syntax

Rules are boolean expressions using StockIndicators field names with comparison operators and AND/OR logic.

Examples:
- `change_pct_13w > 10 AND max_drop_pct_2w < 15`
- `r_squared_52w > 0.7 AND change_pct_26w > 20 AND max_drawdown_pct_52w < 25`
- `slope_pct_13w > 0.5 AND pct_weeks_positive_52w > 0.55 OR change_pct_52w > 50`
- `price_vs_ma200_pct > 0 AND ma50_vs_ma200_pct > 0 AND change_pct_13w > 10` (long-term uptrend + golden-cross territory + momentum)

## Indicator categories (call `list_indicator_fields` for the full list)

- **Trend / momentum** — slope/log-slope/R² over 13w/26w/52w, change_pct over 1w-52w, acceleration_pct_13w
- **Volatility / risk** — return_std_52w, downside_std_52w, max_drop_pct over 1w/2w/4w, max_drawdown_pct over 4w-52w
- **Up-period frequency** — pct_weeks_positive over 4w-52w
- **Moving-average structure** — price_vs_ma{20,50,100,200}_pct, ma50_vs_ma200_pct (golden/death cross)

## Ranking expression

After filtering, stocks are ranked by a **ranking expression** — a numeric formula using the same \
StockIndicators fields. Higher score = higher priority for selection. You can customize this \
per backtest via the `ranking` parameter.

Default ranking: `change_pct_13w / return_std_52w` (risk-adjusted momentum — return per unit of volatility).

Examples:
- `change_pct_13w / return_std_52w` — risk-adjusted momentum (default)
- `slope_pct_52w * r_squared_52w` — trend quality (strong + consistent)
- `change_pct_26w / max_drawdown_pct_52w` — return per unit of drawdown
- `slope_pct_13w * r_squared_13w + 0.5 * change_pct_4w` — composite: mid-term trend quality + short-term momentum
- `change_pct_13w / downside_std_52w` — upside-to-downside ratio

Ranking matters because it determines which stocks get selected when more pass the filter \
than `max_stocks` allows. Experiment with different rankings alongside rule changes.

## Available tools

- `list_indicator_fields` — Discover available indicator fields and their ranges.
- `preview_filter` — Quickly check how many stocks pass a rule at a given date. Accepts an \
optional `ranking` parameter. Use this to calibrate thresholds before running a full backtest. \
If too few stocks match (<5), loosen constraints; if too many (>50), tighten them.
- `run_backtest` — Run a full backtest with a rule and optional `ranking` expression. \
Returns scores AND diagnostics: worst/best periods, cash periods (where no stocks matched), \
stock selection stats (unique stocks, top-held symbols). \
Optionally pass `stop_loss` to set a per-position stop fixed at buy time: \
`{"type": "percent", "value": 5}` exits 5%% below buy price; \
`{"type": "ma_percent", "value": 95, "ma_period": 50}` exits below 95%% of MA50 at buy.
- `write_strategy_notes` — Save your reasoning, iteration history, and observations as markdown. \
Use this to track what you've tried and what worked.
- `read_strategy_notes` — Read back previous strategy notes or list all saved strategies.
- `lookup_stock` — Look up indicator values for specific stock(s) at a given date. Use this \
to inspect why a particular stock was or wasn't selected, or to understand its characteristics.

## Workflow

1. The user message includes a backtest period — use those dates for your backtests.
2. Start by calling `list_indicator_fields` to see what indicators are available.
3. Based on the user's idea, design an initial rule.
4. Use `preview_filter` on a recent date to check the rule produces a reasonable number of matches.
5. Run a backtest with `run_backtest` using the provided date range.
6. **After each backtest, do three things before moving on:**
   a. **Analyze** the scores AND diagnostics carefully:
      - Check `worst_periods` — if losses cluster in specific dates, consider adding volatility guards.
      - Check `cash_periods` — if too many, the rule is too restrictive.
      - Check `top_held_symbols` — if one stock dominates, the strategy may lack diversification.
      - Aim for Sharpe > 1.0, reasonable drawdown, win rate > 50%.
      - Compare against prior iterations: what improved, what got worse, and why?
   b. **Save notes** by calling `write_strategy_notes` — append your observations for this \
iteration: the rule tested, key metrics, what was good, what was bad, and your hypothesis \
for the next change. Build up a running log across iterations so you have a complete record.
   c. **Form a hypothesis** for what to change next and explain your reasoning \
before running the next backtest (e.g. "Sharpe dropped when I added max_drawdown — \
the filter is too restrictive, causing cash periods. I'll loosen it from 20 to 25.").
7. Run 5-10 backtest iterations per round. Each iteration should be driven by your \
observations from the previous result — do not batch changes blindly. \
Vary across all strategy levers: after a few rule iterations, try different rankings, \
max_stocks values, and rebalance intervals to find the optimal combination.
8. After completing your iterations for this round, present your recommendation: \
the best-performing configuration (rule, ranking, max_stocks, rebalance_interval_weeks), \
key performance metrics, and any insights or trade-offs worth noting \
(e.g. "loosening drawdown improved returns but increased volatility", \
"ranking by downside_std_52w outperformed the default momentum ranking"). \
Then stop and wait for the user's follow-up instruction — they may ask you to explore a \
different direction, tighten specific constraints, or run another round of iterations based \
on what they see in the results.

## Strategy levers

You have multiple levers to tune a strategy — not just the filter rule. You may use all of them:

1. **Rule** — the filter expression that selects which stocks qualify. This is the primary lever.
2. **Ranking** — the expression that prioritizes stocks when more pass the filter than \
`max_stocks` allows. Different rankings can dramatically change which stocks get picked \
even with the same rule. Try at least 2-3 different rankings per round.
3. **max_stocks** — how many stocks to hold simultaneously (default: 3). More stocks = more \
diversification but diluted conviction. Try values from 2 to 5.
4. **rebalance_interval_weeks** — how often to rebalance (default: 2). Shorter intervals \
react faster but incur more trading. Try 1, 2, or 4 weeks.
5. **index** — the stock universe (SP500 or NASDAQ). Different universes have different \
characteristics — NASDAQ is more tech/growth-heavy.

Don't just iterate on the rule. After finding a decent rule, also experiment with ranking, \
max_stocks, and rebalance_interval_weeks to optimize the full strategy.

## Guidelines

- **Think before each iteration**: after every backtest result, explain what you observed, \
what you think caused it, and what specific change you will try next. Never run back-to-back \
backtests without analyzing the previous result first.
- Be systematic: change one thing at a time so you can isolate what helps and what hurts.
- Consider risk: a high-return strategy with huge drawdowns is not good.
- Use `preview_filter` to calibrate before committing to expensive backtests.
- Use diagnostics to understand WHY a strategy fails, not just that it does.
- Use the scoring metrics to make objective decisions, not just total return.
- If a rule produces no results (empty portfolio), loosen the constraints.
- Call `write_strategy_notes` after every single backtest, not just at the end. \
Build a running log so the full iteration history is always saved.
"""

# Known provider prefixes for auto-detection
_OPENAI_MODELS = ("gpt-", "o1", "o3", "o4")
_ANTHROPIC_MODELS = ("claude-",)


def _detect_provider(model: str) -> str:
    """Detect provider from model name. Returns 'anthropic' or 'openai'."""
    model_lower = model.lower()
    if any(model_lower.startswith(p) for p in _OPENAI_MODELS):
        return "openai"
    if any(model_lower.startswith(p) for p in _ANTHROPIC_MODELS):
        return "anthropic"
    # Default to anthropic
    return "anthropic"


# =============================================================================
# Anthropic implementation
# =============================================================================


async def _run_anthropic_stream(
    instruction: str,
    model: str,
    strategy_id: str,
    history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """Run agent loop using Anthropic API."""
    import anthropic

    if not ANTHROPIC_API_KEY:
        yield {
            "event": "error",
            "data": {"message": "ANTHROPIC_API_KEY not set. Add it to your .env file."},
        }
        return

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    if history:
        messages: list[dict] = history + [{"role": "user", "content": instruction}]
    else:
        messages = [{"role": "user", "content": instruction}]

    for iteration in range(20):
        logger.info(f"Agent iteration {iteration + 1} (anthropic/{model})")

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=ANTHROPIC_TOOLS,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
            )
        except Exception as e:
            yield {"event": "error", "data": {"message": f"Anthropic API error: {e}"}}
            return

        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        for block in assistant_content:
            if block.type == "text":
                yield {"event": "text", "data": {"content": block.text}}

        tool_use_blocks = [b for b in assistant_content if b.type == "tool_use"]

        if not tool_use_blocks:
            yield {
                "event": "done",
                "data": {
                    "llm_history": _serialize_anthropic_messages(messages),
                },
            }
            return

        tool_results = []
        for tool_block in tool_use_blocks:
            yield {
                "event": "tool_call",
                "data": {"name": tool_block.name, "input": tool_block.input},
            }
            result_str = await execute_tool(
                tool_block.name, tool_block.input, strategy_id=strategy_id
            )
            yield {
                "event": "tool_result",
                "data": {"name": tool_block.name, "result": json.loads(result_str)},
            }
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_str,
                }
            )

        messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            yield {
                "event": "done",
                "data": {
                    "llm_history": _serialize_anthropic_messages(messages),
                },
            }
            return

    yield {
        "event": "done",
        "data": {"llm_history": _serialize_anthropic_messages(messages)},
    }


# =============================================================================
# OpenAI implementation
# =============================================================================


async def _run_openai_stream(
    instruction: str,
    model: str,
    strategy_id: str,
    history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """Run agent loop using OpenAI API."""
    from openai import AsyncOpenAI

    if not OPENAI_API_KEY:
        yield {
            "event": "error",
            "data": {"message": "OPENAI_API_KEY not set. Add it to your .env file."},
        }
        return

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    if history:
        messages: list[dict] = history + [{"role": "user", "content": instruction}]
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]

    for iteration in range(20):
        logger.info(f"Agent iteration {iteration + 1} (openai/{model})")

        try:
            response = await client.chat.completions.create(
                model=model,
                max_completion_tokens=4096,
                tools=OPENAI_TOOLS,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
            )
        except Exception as e:
            yield {"event": "error", "data": {"message": f"OpenAI API error: {e}"}}
            return

        choice = response.choices[0]
        message = choice.message

        # Yield text content
        if message.content:
            yield {"event": "text", "data": {"content": message.content}}

        # Check for tool calls
        if not message.tool_calls:
            yield {
                "event": "done",
                "data": {"llm_history": json.dumps(messages)},
            }
            return

        # Append assistant message (with tool_calls) to history
        messages.append(message.model_dump())

        # Execute tool calls
        for tool_call in message.tool_calls:
            func = tool_call.function  # type: ignore[union-attr]
            try:
                tool_input = json.loads(func.arguments)
            except json.JSONDecodeError as e:
                # Model emitted malformed JSON (often truncated by max_completion_tokens).
                # Surface the error back as a tool_result so the agent can retry rather
                # than crashing the whole strategy run.
                logger.warning(
                    f"Failed to parse tool arguments for {func.name}: {e}. "
                    f"Raw args: {func.arguments[:200]!r}"
                )
                error_payload = json.dumps(
                    {
                        "error": (
                            f"Failed to parse tool arguments as JSON: {e}. "
                            "The arguments string was likely truncated. "
                            "Please retry with a shorter rule or fewer parameters."
                        )
                    }
                )
                yield {
                    "event": "tool_result",
                    "data": {"name": func.name, "result": json.loads(error_payload)},
                }
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_payload,
                    }
                )
                continue

            yield {
                "event": "tool_call",
                "data": {"name": func.name, "input": tool_input},
            }
            result_str = await execute_tool(
                func.name, tool_input, strategy_id=strategy_id
            )
            yield {
                "event": "tool_result",
                "data": {"name": func.name, "result": json.loads(result_str)},
            }

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                }
            )

        if choice.finish_reason == "stop":
            yield {
                "event": "done",
                "data": {"llm_history": json.dumps(messages)},
            }
            return

    yield {"event": "done", "data": {"llm_history": json.dumps(messages)}}


# =============================================================================
# Strategy name generation
# =============================================================================

NAME_SYSTEM_PROMPT = """\
You generate short, descriptive titles for stock trading strategies.

Given a user's strategy idea, respond with a concise title — 3 to 6 words, \
title case, no quotes, no trailing punctuation. The title should capture the \
essence of the strategy (e.g. "Momentum with Drawdown Guard", "Low-Volatility \
Mean Reversion", "Quality Trend Following"). Output ONLY the title, nothing else.\
"""


def _truncate_fallback_name(instruction: str) -> str:
    name = instruction[:50].strip()
    if len(instruction) > 50:
        name += "..."
    return name


async def generate_strategy_name(instruction: str, model: str) -> str:
    """Generate a short descriptive name for a strategy via the LLM.

    Falls back to a truncated instruction if the API call fails or the key
    is missing, so strategy creation never blocks on naming.
    """
    provider = _detect_provider(model)
    fallback = _truncate_fallback_name(instruction)

    try:
        if provider == "openai":
            if not OPENAI_API_KEY:
                return fallback
            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            openai_response = await openai_client.chat.completions.create(
                model=model,
                max_completion_tokens=32,
                messages=[
                    {"role": "system", "content": NAME_SYSTEM_PROMPT},
                    {"role": "user", "content": instruction},
                ],
            )
            content = openai_response.choices[0].message.content or ""
        else:
            if not ANTHROPIC_API_KEY:
                return fallback
            import anthropic

            anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            anthropic_response = await anthropic_client.messages.create(
                model=model,
                max_tokens=32,
                system=NAME_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": instruction}],
            )
            text_blocks = [
                b.text for b in anthropic_response.content if b.type == "text"
            ]
            content = "".join(text_blocks)
    except Exception as e:
        logger.warning(f"Strategy name generation failed: {e}")
        return fallback

    name = content.strip().strip('"').strip("'").rstrip(".")
    if not name:
        return fallback
    # Clamp to a sane length in case the model ignores instructions.
    return name[:80]


# =============================================================================
# Public API
# =============================================================================

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _build_instruction(
    instruction: str, date_start: date | None, date_end: date | None
) -> str:
    """Prepend backtest date range context to the user instruction."""
    end = date_end or date.today()
    start = date_start or (end - timedelta(days=365 * 3))
    return f"Backtest period: {start.isoformat()} to {end.isoformat()}\n\n{instruction}"


async def run_agent_stream(
    instruction: str,
    model: str = DEFAULT_MODEL,
    date_start: date | None = None,
    date_end: date | None = None,
    history: list[dict] | None = None,
    *,
    strategy_id: str,
) -> AsyncGenerator[dict, None]:
    """Run the strategy agent, yielding SSE-compatible event dicts.

    Automatically detects provider from model name:
    - "claude-*" → Anthropic
    - "gpt-*", "o1*", "o3*", "o4*" → OpenAI

    Args:
        history: Prior LLM messages for multi-turn continuation.
        strategy_id: Strategy UUID string for linking backtests.

    Yields dicts with keys: {"event": str, "data": dict}
    Event types: text, tool_call, tool_result, done, error
    The "done" event includes "llm_history" — the serialized LLM messages
    for persistence and future continuation.
    """
    provider = _detect_provider(model)
    logger.info(f"Using provider: {provider}, model: {model}")

    full_instruction = _build_instruction(instruction, date_start, date_end)

    if provider == "openai":
        async for event in _run_openai_stream(
            full_instruction, model, history=history, strategy_id=strategy_id
        ):
            yield event
    else:
        async for event in _run_anthropic_stream(
            full_instruction, model, history=history, strategy_id=strategy_id
        ):
            yield event
