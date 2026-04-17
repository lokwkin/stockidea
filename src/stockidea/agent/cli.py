"""CLI commands for agent operations."""

import asyncio
import json
import logging
from datetime import date, timedelta

import click

from stockidea.datasource.database import conn
from stockidea.datasource.database.queries import (
    create_strategy,
    add_strategy_message,
    update_strategy_status,
    update_strategy_llm_history,
)
from stockidea.types import StrategyCreate

logger = logging.getLogger(__name__)


@click.group("agent")
def agent_cli():
    """AI agent commands."""
    pass


@agent_cli.command(
    "agent", help="Run the AI strategy agent with a natural language instruction."
)
@click.option(
    "--instruction",
    "-i",
    type=str,
    required=True,
    help="Strategy idea in natural language",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default="claude-sonnet-4-20250514",
    help="Anthropic model to use",
)
@click.option(
    "--date-start",
    type=str,
    default=None,
    help="Backtest start date (YYYY-MM-DD). Default: 3 years before date-end",
)
@click.option(
    "--date-end",
    type=str,
    default=None,
    help="Backtest end date (YYYY-MM-DD). Default: today",
)
def agent(instruction: str, model: str, date_start: str | None, date_end: str | None):
    from stockidea.agent.agent import run_agent_stream

    ds = date.fromisoformat(date_start) if date_start else None
    de = date.fromisoformat(date_end) if date_end else None
    end = de or date.today()
    start = ds or (end - timedelta(days=365 * 3))

    click.echo("Starting AI strategy agent...")
    click.echo(f"Instruction: {instruction}")
    click.echo(f"Model: {model}")
    click.echo("---")

    async def _run():
        # Create strategy in DB
        strategy_create = StrategyCreate(
            instruction=instruction, model=model, date_start=ds, date_end=de
        )
        name = instruction[:50].strip()
        if len(instruction) > 50:
            name += "..."

        async with conn.get_db_session() as db_session:
            strategy_id = await create_strategy(
                db_session, strategy_create, name=name, date_start=start, date_end=end
            )

        strategy_id_str = str(strategy_id)

        # Save user message
        async with conn.get_db_session() as db_session:
            await add_strategy_message(
                db_session,
                strategy_id,
                role="user",
                content_json=json.dumps({"text": instruction}),
            )
            await update_strategy_status(db_session, strategy_id, "running")

        # Run agent and collect events
        texts: list[str] = []
        agent_events: list[dict] = []
        llm_history: str | None = None

        async for event in run_agent_stream(
            instruction,
            model,
            date_start=start,
            date_end=end,
            strategy_id=strategy_id_str,
        ):
            event_type = event["event"]
            if event_type == "text":
                content = event["data"]["content"]
                texts.append(content)
                print(content)
                agent_events.append(event)
            elif event_type == "done":
                llm_history = event["data"].get("llm_history")
            elif event_type == "error":
                agent_events.append(event)
                raise ValueError(event["data"]["message"])
            else:
                agent_events.append(event)

        # Persist agent response and LLM history
        async with conn.get_db_session() as db_session:
            await add_strategy_message(
                db_session,
                strategy_id,
                role="assistant",
                content_json=json.dumps(agent_events),
            )
            if llm_history:
                await update_strategy_llm_history(db_session, strategy_id, llm_history)
            await update_strategy_status(db_session, strategy_id, "idle")

        click.echo(f"\nStrategy saved with ID: {strategy_id}")
        return "\n".join(texts)

    final_response = asyncio.run(_run())

    click.echo("---")
    click.echo("Final recommendation:")
    click.echo(final_response)
