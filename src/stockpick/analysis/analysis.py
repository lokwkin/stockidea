
from dataclasses import asdict
from datetime import datetime, timedelta
import json
from typing import Callable

from stockpick.analysis import trend_analyzer
from stockpick.config import OUTPUT_DIR
from stockpick.types import StockPrice, TrendAnalysis


def apply_rule(analyses: list[TrendAnalysis], max_stocks: int, rule_func: Callable[[TrendAnalysis], bool]
               ) -> list[TrendAnalysis]:

    filtered_stocks = [analysis for analysis in analyses if rule_func(analysis)]

    # Sort by weight
    # TODO: use a more sophisticated algorithm
    filtered_stocks.sort(key=lambda x: x.trend_slope_pct, reverse=True)
    selected_stocks = filtered_stocks[: max_stocks]
    print(f"Selected: {[stock.symbol for stock in selected_stocks]} (from {len(filtered_stocks)} filtered)")
    return selected_stocks


def analyze_stock_batch(stock_prices: dict[str, list[StockPrice]], analysis_date: datetime, back_period_weeks: int = 52) -> tuple[list[TrendAnalysis], str]:
    analyses: list[TrendAnalysis] = []
    for symbol, prices in stock_prices.items():
        analysis = trend_analyzer.analyze_stock(
            symbol=symbol, prices=prices, from_date=analysis_date - timedelta(weeks=back_period_weeks), to_date=analysis_date)
        if analysis:
            analyses.append(analysis)

    print(f"\nAnalyzed {len(analyses)} stocks successfully")
    filename = save_analysis(analysis=analyses, analysis_date=analysis_date)
    return analyses, filename


def save_analysis(analysis: list[TrendAnalysis], analysis_date: datetime) -> str:
    analysis_data = [asdict(a) for a in analysis]
    filename = f"analysis_{analysis_date.strftime('%Y%m%d')}.json"
    analysis_path = OUTPUT_DIR / "analysis" / filename
    analysis_path.write_text(
        json.dumps(
            {
                "analysis_date": analysis_date.strftime("%Y%m%d"),
                "data": analysis_data,
            },
            indent=2,
        )
    )
    print(f"✓ Analysis saved: {analysis_path}")
    return filename
