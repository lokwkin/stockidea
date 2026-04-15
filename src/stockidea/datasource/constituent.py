from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from stockidea.datasource import fmp
from stockidea.datasource.database import queries
from stockidea.types import ConstituentChange, StockIndex


async def _load_constituent_changes(
    db_session: AsyncSession, index: StockIndex
) -> list[ConstituentChange]:
    """Load constituent changes from DB, fetching from FMP if stale."""
    cached = await queries.load_constituent_changes(db_session, index)
    if cached is not None:
        return cached
    changes = await fmp.fetch_historical_constituent(index)
    await queries.save_constituent_changes(db_session, index, changes)
    return changes


async def get_constituent_at(
    db_session: AsyncSession, index: StockIndex, target_date: date
) -> list[str]:
    """Get the constituent symbols of the index at the target date.

    Loads constituent change history and reconstructs membership at the given date.
    """
    changes = await _load_constituent_changes(db_session, index)
    symbols = set()
    for change in changes:
        if change.date > target_date:
            break
        if change.removed_symbol:
            symbols.discard(change.removed_symbol)
        if change.added_symbol:
            symbols.add(change.added_symbol)
    return sorted(symbols)
