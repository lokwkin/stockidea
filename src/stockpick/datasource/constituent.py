from datetime import date
from stockpick.datasource import fmp, file_cache
from stockpick.types import ConstituentChange, StockIndex


async def _load_constituent_changes(index: StockIndex) -> list[ConstituentChange]:
    cached_changes = file_cache.load_from_cache(f"constituent_changes_{index.value}")
    if cached_changes is not None:
        return [ConstituentChange.model_validate(change) for change in cached_changes]
    changes = await fmp.fetch_historical_constituent(index)
    file_cache.save_to_cache(f"constituent_changes_{index.value}", [change.model_dump(mode="json") for change in changes])
    return changes


async def get_constituent_at(index: StockIndex, target_date: date) -> list[str]:
    """
    Get the constituent of the index at the target date.
    Load the constituent changes and re-construct the constituent at the target date.
    """
    changes = await _load_constituent_changes(index)
    symbols = set()
    for change in changes:
        # Stop processing if we've passed the target date
        if change.date > target_date:
            break

        # Remove the old symbol first (if it exists)
        if change.removed_symbol:
            symbols.discard(change.removed_symbol)

        # Add the new symbol
        if change.added_symbol:
            symbols.add(change.added_symbol)

    # Return sorted list
    return sorted(symbols)
