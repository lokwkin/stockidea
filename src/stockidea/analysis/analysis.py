
from datetime import datetime, timedelta
import json
import logging
from typing import Callable

from stockidea.analysis import trend_analyzer
from stockidea.config import ANALYSIS_DIR
from stockidea.types import StockPrice, TrendAnalysis

logger = logging.getLogger(__name__)


def apply_rule(analyses: list[TrendAnalysis], rule_func: Callable[[TrendAnalysis], bool]
               ) -> list[TrendAnalysis]:

    filtered_stocks = [analysis for analysis in analyses if rule_func(analysis)]

    # Sort by rising stability score
    filtered_stocks = trend_analyzer.rank_by_rising_stability_score(filtered_stocks)

    # Remove outliers from the list of TrendAnalysis objects based on the linear slope percentage
    filtered_stocks = trend_analyzer.slope_outlier_mask(filtered_stocks, k=3.0)

    return filtered_stocks


def analyze_stock_batch(stock_prices: dict[str, list[StockPrice]], analysis_date: datetime, back_period_weeks: int = 52) -> tuple[list[TrendAnalysis], str]:
    analyses: list[TrendAnalysis] = []
    for symbol, prices in stock_prices.items():
        analysis = trend_analyzer.analyze_stock(
            symbol=symbol, prices=prices, from_date=analysis_date - timedelta(weeks=back_period_weeks), to_date=analysis_date)
        if analysis:
            analyses.append(analysis)

    logger.info(f"Analyzed {len(analyses)} stocks successfully")
    filename = save_analysis(analysis=analyses, analysis_date=analysis_date)
    return analyses, filename


def load_analysis(analysis_date: datetime) -> tuple[list[TrendAnalysis], str] | None:
    filename = f"analysis_{analysis_date.strftime('%Y%m%d')}.json"
    analysis_path = ANALYSIS_DIR / filename
    if not analysis_path.exists():
        return None
    analysis_data = json.loads(analysis_path.read_text())
    return [TrendAnalysis.model_validate(item) for item in analysis_data["data"]], filename


def save_analysis(analysis: list[TrendAnalysis], analysis_date: datetime) -> str:
    analysis_data = [a.model_dump() for a in analysis]
    filename = f"analysis_{analysis_date.strftime('%Y%m%d')}.json"
    analysis_path = ANALYSIS_DIR / filename
    analysis_path.write_text(
        json.dumps(
            {
                "analysis_date": analysis_date.strftime("%Y%m%d"),
                "data": analysis_data,
            },
            indent=2,
        )
    )
    logger.info(f"✓ Analysis saved: {analysis_path}")
    return filename
