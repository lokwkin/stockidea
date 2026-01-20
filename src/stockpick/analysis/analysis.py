
from dataclasses import asdict
from datetime import datetime
import json

from stockpick.analysis.price_analyzer import PriceAnalysis, analyze_stock_batch
from stockpick.fetch_prices import fetch_stock_prices_batch
from stockpick.config import OUTPUT_DIR


def analyze_batch(symbols: list[str], period_start: datetime, period_end: datetime) -> str:
    analyses: list[PriceAnalysis] = []

    stock_prices = fetch_stock_prices_batch(symbols)
    analyses = analyze_stock_batch(stock_prices=stock_prices, from_date=period_start.date(), to_date=period_end.date())

    print(f"\nAnalyzed {len(analyses)} stocks successfully")

    filename = save_analysis(analysis=analyses, analysis_date=period_end)
    return filename


def save_analysis(analysis: list[PriceAnalysis], analysis_date: datetime) -> str:
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
