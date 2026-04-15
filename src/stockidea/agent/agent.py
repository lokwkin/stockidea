"""AI strategy agent that translates human ideas into backtested trading rules."""

import json
import logging
from typing import AsyncGenerator

from stockidea.agent.tools import ANTHROPIC_TOOLS, OPENAI_TOOLS, execute_tool
from stockidea.constants import ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)

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
- `change_13w_pct > 10 AND max_drop_2w_pct < 15`
- `linear_r_squared > 0.7 AND change_26w_pct > 20 AND max_drawdown_pct < 25`
- `slope_13w_pct > 0.5 AND pct_weeks_positive > 0.55 OR change_1y_pct > 50`

## Available tools

- `list_indicator_fields` — Discover available indicator fields and their ranges.
- `preview_filter` — Quickly check how many stocks pass a rule at a given date. Use this \
to calibrate thresholds before running a full backtest. If too few stocks match (<5), \
loosen constraints; if too many (>50), tighten them.
- `run_backtest` — Run a full backtest. Returns scores AND diagnostics: worst/best periods, \
cash periods (where no stocks matched), stock selection stats (unique stocks, top-held symbols).
- `write_strategy_notes` — Save your reasoning, iteration history, and observations as markdown. \
Use this to track what you've tried and what worked.
- `read_strategy_notes` — Read back previous strategy notes or list all saved strategies.

## Workflow

1. Start by calling `list_indicator_fields` to see what indicators are available.
2. Based on the user's idea, design an initial rule.
3. Use `preview_filter` on a recent date to check the rule produces a reasonable number of matches.
4. Run a backtest with `run_backtest` to test it.
5. Analyze the scores AND diagnostics:
   - Check `worst_periods` — if losses cluster in specific dates, consider adding volatility guards.
   - Check `cash_periods` — if too many, the rule is too restrictive.
   - Check `top_held_symbols` — if one stock dominates, the strategy may lack diversification.
   - Aim for Sharpe > 1.0, reasonable drawdown, win rate > 50%.
6. Iterate: adjust thresholds, add/remove conditions, try different parameters.
7. Save your notes with `write_strategy_notes` to track your reasoning and iterations.
8. Run 2-5 iterations to find a good balance.
9. Present your final recommendation with the rule and key performance metrics.

## Guidelines

- Be systematic: change one thing at a time so you can understand what helps.
- Consider risk: a high-return strategy with huge drawdowns is not good.
- Use `preview_filter` to calibrate before committing to expensive backtests.
- Use diagnostics to understand WHY a strategy fails, not just that it does.
- Use the scoring metrics to make objective decisions, not just total return.
- Explain your reasoning to the user after each iteration.
- If a rule produces no results (empty portfolio), loosen the constraints.
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
    instruction: str, model: str
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
    messages: list[dict] = [{"role": "user", "content": instruction}]

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
            yield {"event": "done", "data": {}}
            return

        tool_results = []
        for tool_block in tool_use_blocks:
            yield {
                "event": "tool_call",
                "data": {"name": tool_block.name, "input": tool_block.input},
            }
            result_str = await execute_tool(tool_block.name, tool_block.input)
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
            yield {"event": "done", "data": {}}
            return

    yield {"event": "done", "data": {}}


# =============================================================================
# OpenAI implementation
# =============================================================================


async def _run_openai_stream(
    instruction: str, model: str
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
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": instruction},
    ]

    for iteration in range(20):
        logger.info(f"Agent iteration {iteration + 1} (openai/{model})")

        try:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=4096,
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
            yield {"event": "done", "data": {}}
            return

        # Append assistant message (with tool_calls) to history
        messages.append(message.model_dump())

        # Execute tool calls
        for tool_call in message.tool_calls:
            func = tool_call.function  # type: ignore[union-attr]
            tool_input = json.loads(func.arguments)

            yield {
                "event": "tool_call",
                "data": {"name": func.name, "input": tool_input},
            }
            result_str = await execute_tool(func.name, tool_input)
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
            yield {"event": "done", "data": {}}
            return

    yield {"event": "done", "data": {}}


# =============================================================================
# Public API
# =============================================================================

DEFAULT_MODEL = "claude-sonnet-4-20250514"


async def run_agent_stream(
    instruction: str, model: str = DEFAULT_MODEL
) -> AsyncGenerator[dict, None]:
    """Run the strategy agent, yielding SSE-compatible event dicts.

    Automatically detects provider from model name:
    - "claude-*" → Anthropic
    - "gpt-*", "o1*", "o3*", "o4*" → OpenAI

    Yields dicts with keys: {"event": str, "data": dict}
    Event types: text, tool_call, tool_result, done, error
    """
    provider = _detect_provider(model)
    logger.info(f"Using provider: {provider}, model: {model}")

    if provider == "openai":
        async for event in _run_openai_stream(instruction, model):
            yield event
    else:
        async for event in _run_anthropic_stream(instruction, model):
            yield event


async def run_agent(instruction: str, model: str = DEFAULT_MODEL) -> str:
    """Run the strategy agent (non-streaming, for CLI use).

    Returns the agent's final text response.
    """
    texts: list[str] = []
    async for event in run_agent_stream(instruction, model):
        if event["event"] == "text":
            content = event["data"]["content"]
            texts.append(content)
            print(content)
        elif event["event"] == "error":
            raise ValueError(event["data"]["message"])
    return "\n".join(texts)
