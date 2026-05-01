from datetime import datetime, timedelta
import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession


from stockidea.indicators import calculator
from stockidea.datasource import service as datasource_service
from stockidea.datasource.database import queries
from stockidea.types import MarketRegime, StockIndex, StockIndicators

logger = logging.getLogger(__name__)

# Periods we pre-load SMA / RS for. Mirrors datasource_service.SMA_PERIODS_STOCK.
_SMA_PERIODS = [20, 50, 100, 200]
_RS_WINDOWS = [4, 13, 26, 52]


def apply_rule(
    indicators_batch: list[StockIndicators],
    rule_func: Callable[[StockIndicators], bool] | None = None,
    ranking_func: Callable[[StockIndicators], float] | None = None,
) -> list[StockIndicators]:
    from stockidea.rule_engine import compile_ranking, DEFAULT_RANKING

    if rule_func is None:
        filtered_stocks = list(indicators_batch)
    else:
        filtered_stocks = [
            indicator for indicator in indicators_batch if rule_func(indicator)
        ]

    # Rank by expression (default: risk-adjusted momentum)
    if ranking_func is None:
        ranking_func = compile_ranking(DEFAULT_RANKING)
    filtered_stocks = calculator.rank_by_expression(filtered_stocks, ranking_func)

    # Remove outliers based on the linear slope percentage
    filtered_stocks = calculator.slope_outlier_mask(filtered_stocks, k=3.0)

    return filtered_stocks


async def get_stock_indicators_batch(
    db_session: AsyncSession,
    symbols: list[str],
    indicators_date: datetime,
    back_period_weeks: int = 52,
    compute_if_not_exists: bool = False,
    from_index: StockIndex | None = None,
) -> list[StockIndicators]:
    """Load (or compute) StockIndicators for each symbol.

    When `from_index` is provided, also computes/loads market regime for that index
    and merges the regime fields (`mkt_*`) into every returned StockIndicators.
    Computed indicators receive MA structure (`price_vs_ma*`, `ma50_vs_ma200_pct`)
    and relative strength (`rs_pct_*w`) fields based on the index.
    """
    from_date = indicators_date - timedelta(weeks=back_period_weeks)
    to_date = indicators_date

    # Pre-compute benchmark window changes (for RS) and regime (mkt_*) when index given.
    benchmark_changes_pct: dict[int, float] = {}
    regime_update: dict[str, float | int] = {}
    if from_index is not None:
        benchmark_changes_pct = await _compute_benchmark_changes_pct(
            db_session, from_index, indicators_date
        )
        regime = await _ensure_market_regime(
            db_session, from_index, indicators_date.date()
        )
        if regime is not None:
            regime_update = {
                "mkt_index_above_ma50": regime.index_above_ma50,
                "mkt_index_above_ma200": regime.index_above_ma200,
                "mkt_index_drawdown_pct_52w": regime.index_drawdown_pct_52w,
                "mkt_breadth_pct_above_ma50": regime.breadth_pct_above_ma50,
                "mkt_breadth_pct_above_ma200": regime.breadth_pct_above_ma200,
            }

    results: list[StockIndicators] = []
    for symbol in symbols:
        try:
            stock_indicators = await queries.load_stock_indicators(
                db_session, symbol, indicators_date.date()
            )
            if not stock_indicators and compute_if_not_exists:
                prices = await datasource_service.get_stock_price_history(
                    db_session, symbol, from_date, to_date
                )
                sma_lookup: dict[int, float | None] = {}
                for period_length in _SMA_PERIODS:
                    try:
                        sma_lookup[
                            period_length
                        ] = await datasource_service.get_sma_at_date(
                            db_session, symbol, period_length, indicators_date.date()
                        )
                    except Exception as e:
                        logger.warning(
                            f"SMA({period_length}) unavailable for {symbol}: {e}"
                        )
                        sma_lookup[period_length] = None

                stock_indicators = calculator.compute_stock_indicators(
                    symbol=symbol,
                    prices=prices,
                    from_date=indicators_date - timedelta(weeks=back_period_weeks),
                    to_date=indicators_date,
                    sma_lookup=sma_lookup,
                    benchmark_changes_pct=benchmark_changes_pct,
                )
                # Save to database for cache (mkt_* fields are stripped at save)
                await queries.save_stock_indicators(
                    db_session, stock_indicators, indicators_date.date()
                )

            if stock_indicators:
                if regime_update:
                    stock_indicators = stock_indicators.model_copy(update=regime_update)
                results.append(stock_indicators)
        except Exception as e:
            logger.error(f"Error computing stock indicators for {symbol}: {e}")

    return results


async def _compute_benchmark_changes_pct(
    db_session: AsyncSession,
    index: StockIndex,
    indicators_date: datetime,
) -> dict[int, float]:
    """Pre-compute the benchmark index's %-change over each RS window."""
    earliest = indicators_date - timedelta(weeks=max(_RS_WINDOWS) + 4)
    prices = await datasource_service.get_index_prices(
        db_session, index, earliest.date(), indicators_date.date()
    )
    if not prices:
        return {}

    # `prices` is ordered desc by date (per get_prices_by_date_range).
    prices_asc = sorted(prices, key=lambda p: p.date)
    current_price = prices_asc[-1].adj_close
    target_date = prices_asc[-1].date

    changes: dict[int, float] = {}
    for weeks in _RS_WINDOWS:
        ref_date = target_date - timedelta(weeks=weeks)
        # Use the price closest on/before ref_date.
        ref_price = None
        for p in reversed(prices_asc):
            if p.date <= ref_date:
                ref_price = p.adj_close
                break
        if ref_price is None or ref_price == 0:
            changes[weeks] = 0.0
        else:
            changes[weeks] = (current_price - ref_price) / ref_price * 100
    return changes


async def _ensure_market_regime(
    db_session: AsyncSession,
    index: StockIndex,
    target_date,
) -> MarketRegime | None:
    """Load cached MarketRegime for (index, date) or compute + cache it."""
    cached = await queries.load_market_regime(db_session, index, target_date)
    if cached is not None:
        return cached

    try:
        regime = await _compute_market_regime(db_session, index, target_date)
    except Exception as e:
        logger.error(
            f"Failed to compute market regime for {index.value} on {target_date}: {e}"
        )
        return None

    if regime is not None:
        try:
            await queries.save_market_regime(db_session, regime)
        except Exception as e:
            logger.error(f"Failed to save market regime: {e}")
    return regime


async def _compute_market_regime(
    db_session: AsyncSession,
    index: StockIndex,
    target_date,
) -> MarketRegime | None:
    """Compute regime from scratch using cached prices + SMA series."""
    fmp_symbol = datasource_service.index_fmp_symbol(index)

    # Index price + SMAs at the target date.
    try:
        index_price = await datasource_service.get_index_price_at_date(
            db_session, index, target_date, nearest=True
        )
    except ValueError:
        return None

    sma50_index = await datasource_service.get_sma_at_date(
        db_session, fmp_symbol, 50, target_date
    )
    sma200_index = await datasource_service.get_sma_at_date(
        db_session, fmp_symbol, 200, target_date
    )

    index_above_ma50 = (
        1 if sma50_index is not None and index_price.adj_close > sma50_index else 0
    )
    index_above_ma200 = (
        1 if sma200_index is not None and index_price.adj_close > sma200_index else 0
    )

    # 52-week drawdown of the index (current vs trailing 52w peak, positive %)
    earliest = target_date - timedelta(weeks=52)
    index_history = await datasource_service.get_index_prices(
        db_session, index, earliest, target_date
    )
    if index_history:
        peak = max(p.adj_close for p in index_history)
        if peak > 0:
            index_drawdown_pct_52w = max(
                0.0, (peak - index_price.adj_close) / peak * 100
            )
        else:
            index_drawdown_pct_52w = 0.0
    else:
        index_drawdown_pct_52w = 0.0

    # Breadth: % of constituents whose latest price is above their MA50 / MA200.
    constituents = await datasource_service.get_constituent_at(
        db_session, index, target_date
    )
    breadth_pct_above_ma50 = await _compute_breadth(
        db_session, constituents, period_length=50, target_date=target_date
    )
    breadth_pct_above_ma200 = await _compute_breadth(
        db_session, constituents, period_length=200, target_date=target_date
    )

    return MarketRegime(
        index=index,
        date=target_date,
        index_above_ma50=index_above_ma50,
        index_above_ma200=index_above_ma200,
        index_drawdown_pct_52w=index_drawdown_pct_52w,
        breadth_pct_above_ma50=breadth_pct_above_ma50,
        breadth_pct_above_ma200=breadth_pct_above_ma200,
    )


async def _compute_breadth(
    db_session: AsyncSession,
    symbols: list[str],
    period_length: int,
    target_date,
) -> float:
    """Fraction of given symbols whose latest price is above their SMA(period_length)."""
    if not symbols:
        return 0.0
    sma_map = await queries.get_latest_sma_per_symbol(
        db_session, symbols, period_length, target_date
    )
    price_map = await queries.get_latest_price_per_symbol(
        db_session, symbols, target_date
    )
    above = 0
    counted = 0
    for symbol in symbols:
        upper = symbol.upper()
        sma = sma_map.get(upper)
        price = price_map.get(upper)
        if sma is None or price is None:
            continue
        counted += 1
        if price > sma:
            above += 1
    if counted == 0:
        return 0.0
    return above / counted


async def list_indicator_dates(db_session: AsyncSession) -> list[datetime]:
    return await queries.list_indicator_dates(db_session)
