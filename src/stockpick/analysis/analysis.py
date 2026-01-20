
from dataclasses import asdict
from datetime import datetime, timedelta
import json

from stockpick.analysis.price_analyzer import PriceAnalysis, analyze_stock
from stockpick.fetch_prices import fetch_stock_prices
import stockpick.stock_loader as stock_loader
from stockpick.config import OUTPUT_DIR


def generate_report(analysis_date: datetime):
    symbols = stock_loader.load_sp_500()
    analyses: list[PriceAnalysis] = []

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Analyzing {symbol}...", end="\r")
        try:
            prices = fetch_stock_prices(symbol)
            start_from = analysis_date - timedelta(weeks=52 * 1)
            analysis = analyze_stock(prices, from_date=start_from.date(), to_date=analysis_date.date())
            if not analysis:
                continue
            analyses.append(analysis)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            continue

    # Filter out None analyses
    valid_analyses = [a for a in analyses if a is not None]
    print(f"\nAnalyzed {len(valid_analyses)} stocks successfully")

    # Save analysis data to JSON
    analysis_path = OUTPUT_DIR / "analysis" / f"analysis_{analysis_date.strftime('%Y%m%d')}.json"
    analysis_data = [asdict(a) for a in valid_analyses]
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
