"""API routes for strategy and agent operations."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from stockidea.datasource.database import conn, queries
from stockidea.types import StrategyCreate, StrategySummary, StrategyDetail

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.post("/strategies")
async def create_strategy(request: StrategyCreate):
    """Create a new strategy and start the first agent run via SSE."""
    from datetime import date, timedelta

    from stockidea.agent.agent import run_agent_stream

    end = request.date_end or date.today()
    start = request.date_start or (end - timedelta(days=365 * 3))

    # Generate a name from the first ~50 chars of the instruction
    name = request.instruction[:50].strip()
    if len(request.instruction) > 50:
        name += "..."

    async with conn.get_db_session() as db_session:
        strategy_id = await queries.create_strategy(
            db_session, request, name=name, date_start=start, date_end=end
        )

    # Save user message
    async with conn.get_db_session() as db_session:
        await queries.add_strategy_message(
            db_session,
            strategy_id,
            role="user",
            content_json=json.dumps({"text": request.instruction}),
        )

    strategy_id_str = str(strategy_id)

    async def event_stream():
        # First emit the strategy ID so the frontend knows where to navigate
        yield f"event: strategy_created\ndata: {json.dumps({'strategy_id': strategy_id_str})}\n\n"

        async with conn.get_db_session() as db_session:
            await queries.update_strategy_status(db_session, strategy_id, "running")

        agent_events: list[dict] = []
        llm_history: str | None = None
        try:
            async for event in run_agent_stream(
                request.instruction,
                request.model,
                date_start=start,
                date_end=end,
                strategy_id=strategy_id_str,
            ):
                event_type = event["event"]

                if event_type == "done":
                    llm_history = event["data"].get("llm_history")
                    # Don't include llm_history in the SSE data sent to frontend
                    yield f"event: done\ndata: {json.dumps({})}\n\n"
                else:
                    agent_events.append(event)
                    data = json.dumps(event["data"])
                    yield f"event: {event_type}\ndata: {data}\n\n"

        except Exception as e:
            logger.exception(f"Agent stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            async with conn.get_db_session() as db_session:
                await queries.update_strategy_status(db_session, strategy_id, "failed")
            return

        # Persist agent events as a message
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

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class FollowUpRequest(BaseModel):
    instruction: str


@router.post("/strategies/{strategy_id}/messages")
async def send_strategy_message(strategy_id: UUID, request: FollowUpRequest):
    """Send a follow-up message to a strategy and run the agent with prior context."""

    from stockidea.agent.agent import run_agent_stream

    # Load strategy and its LLM history
    async with conn.get_db_session() as db_session:
        strategy = await queries.get_strategy_by_id(db_session, strategy_id)

    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status == "running":
        raise HTTPException(status_code=409, detail="Strategy is already running")

    # Parse LLM history for continuation
    history: list[dict] | None = None
    if strategy.llm_history_json:
        try:
            history = json.loads(strategy.llm_history_json)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM history for strategy {strategy_id}")

    # Save user follow-up message
    async with conn.get_db_session() as db_session:
        await queries.add_strategy_message(
            db_session,
            strategy_id,
            role="user",
            content_json=json.dumps({"text": request.instruction}),
        )

    strategy_id_str = str(strategy_id)

    async def event_stream():
        async with conn.get_db_session() as db_session:
            await queries.update_strategy_status(db_session, strategy_id, "running")

        agent_events: list[dict] = []
        llm_history_result: str | None = None
        try:
            async for event in run_agent_stream(
                request.instruction,
                strategy.model,
                date_start=strategy.date_start,
                date_end=strategy.date_end,
                history=history,
                strategy_id=strategy_id_str,
            ):
                event_type = event["event"]

                if event_type == "done":
                    llm_history_result = event["data"].get("llm_history")
                    yield f"event: done\ndata: {json.dumps({})}\n\n"
                else:
                    agent_events.append(event)
                    data = json.dumps(event["data"])
                    yield f"event: {event_type}\ndata: {data}\n\n"

        except Exception as e:
            logger.exception(f"Agent stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            async with conn.get_db_session() as db_session:
                await queries.update_strategy_status(db_session, strategy_id, "failed")
            return

        # Persist agent events as a message
        async with conn.get_db_session() as db_session:
            await queries.add_strategy_message(
                db_session,
                strategy_id,
                role="assistant",
                content_json=json.dumps(agent_events),
            )
            if llm_history_result:
                await queries.update_strategy_llm_history(
                    db_session, strategy_id, llm_history_result
                )
            await queries.update_strategy_status(db_session, strategy_id, "idle")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: UUID):
    """Delete a strategy and all its messages."""
    async with conn.get_db_session() as db_session:
        deleted = await queries.delete_strategy(db_session, strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"status": "deleted"}
