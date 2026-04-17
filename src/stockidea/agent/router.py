"""API routes for strategy and agent operations."""

import asyncio
import json
import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from stockidea.datasource.database import conn, queries
from stockidea.types import StrategyCreate, StrategySummary, StrategyDetail

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_agent_and_persist(
    strategy_id: UUID,
    instruction: str,
    model: str,
    date_start: date,
    date_end: date,
    history: list[dict] | None = None,
) -> None:
    """Run the agent to completion in the background and persist results.

    Owns its own DB sessions so it survives the originating HTTP request.
    """
    from stockidea.agent.agent import run_agent_stream

    strategy_id_str = str(strategy_id)

    async with conn.get_db_session() as db_session:
        await queries.update_strategy_status(db_session, strategy_id, "running")

    agent_events: list[dict] = []
    llm_history: str | None = None
    try:
        async for event in run_agent_stream(
            instruction,
            model,
            date_start=date_start,
            date_end=date_end,
            history=history,
            strategy_id=strategy_id_str,
        ):
            if event["event"] == "done":
                llm_history = event["data"].get("llm_history")
            else:
                agent_events.append(event)
    except Exception as e:
        logger.exception(f"Agent run failed for strategy {strategy_id}: {e}")
        agent_events.append({"event": "error", "data": {"message": str(e)}})
        async with conn.get_db_session() as db_session:
            if agent_events:
                await queries.add_strategy_message(
                    db_session,
                    strategy_id,
                    role="assistant",
                    content_json=json.dumps(agent_events),
                )
            await queries.update_strategy_status(db_session, strategy_id, "failed")
        return

    async with conn.get_db_session() as db_session:
        await queries.add_strategy_message(
            db_session,
            strategy_id,
            role="assistant",
            content_json=json.dumps(agent_events),
        )
        if llm_history:
            await queries.update_strategy_llm_history(
                db_session, strategy_id, llm_history
            )
        await queries.update_strategy_status(db_session, strategy_id, "idle")


@router.get("/strategies")
async def list_strategies() -> list[StrategySummary]:
    """List all strategies."""
    async with conn.get_db_session() as db_session:
        return await queries.list_strategies(db_session)


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: UUID) -> StrategyDetail:
    """Get a strategy with its messages and linked backtests."""
    async with conn.get_db_session() as db_session:
        strategy = await queries.get_strategy_by_id(db_session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.get("/strategies/{strategy_id}/notes")
async def get_strategy_notes(strategy_id: UUID) -> dict:
    """Return the markdown notes the agent wrote for this strategy, if any."""
    from stockidea.agent.tools import STRATEGIES_DIR

    filepath = STRATEGIES_DIR / f"{strategy_id}.md"
    if not filepath.exists():
        return {"content": None}
    return {"content": filepath.read_text(encoding="utf-8")}


@router.post("/strategies")
async def create_strategy(request: StrategyCreate) -> dict:
    """Create a new strategy and start the agent in the background."""
    from datetime import timedelta

    from stockidea.agent.agent import generate_strategy_name

    end = request.date_end or date.today()
    start = request.date_start or (end - timedelta(days=365 * 3))

    name = await generate_strategy_name(request.instruction, request.model)

    async with conn.get_db_session() as db_session:
        strategy_id = await queries.create_strategy(
            db_session, request, name=name, date_start=start, date_end=end
        )
        await queries.add_strategy_message(
            db_session,
            strategy_id,
            role="user",
            content_json=json.dumps({"text": request.instruction}),
        )

    asyncio.create_task(
        _run_agent_and_persist(
            strategy_id=strategy_id,
            instruction=request.instruction,
            model=request.model,
            date_start=start,
            date_end=end,
        )
    )

    return {"strategy_id": str(strategy_id)}


class FollowUpRequest(BaseModel):
    instruction: str


@router.post("/strategies/{strategy_id}/messages")
async def send_strategy_message(strategy_id: UUID, request: FollowUpRequest) -> dict:
    """Send a follow-up message to a strategy and run the agent in the background."""
    async with conn.get_db_session() as db_session:
        strategy = await queries.get_strategy_by_id(db_session, strategy_id)

    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status == "running":
        raise HTTPException(status_code=409, detail="Strategy is already running")

    history: list[dict] | None = None
    if strategy.llm_history_json:
        try:
            history = json.loads(strategy.llm_history_json)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM history for strategy {strategy_id}")

    async with conn.get_db_session() as db_session:
        await queries.add_strategy_message(
            db_session,
            strategy_id,
            role="user",
            content_json=json.dumps({"text": request.instruction}),
        )

    asyncio.create_task(
        _run_agent_and_persist(
            strategy_id=strategy_id,
            instruction=request.instruction,
            model=strategy.model,
            date_start=strategy.date_start,
            date_end=strategy.date_end,
            history=history,
        )
    )

    return {"status": "running"}


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: UUID) -> dict:
    """Delete a strategy and all its messages."""
    async with conn.get_db_session() as db_session:
        deleted = await queries.delete_strategy(db_session, strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"status": "deleted"}
