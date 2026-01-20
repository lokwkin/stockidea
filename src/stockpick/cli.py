"""CLI commands for stockpick using Click."""

import click
from datetime import datetime

from stockpick import (
    PriceAnalysis,
    Simulator,
    generate_report,
    save_simulation_result,
    stock_loader,
)

from dotenv import load_dotenv

load_dotenv()


@click.group()
def cli():
    """Stock analysis and simulation tool."""
    pass


@cli.command()
@click.argument("date", type=str)
def analyze(date: str):
    try:
        analysis_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {date}. Use YYYY-MM-DD format.")

    generate_report(analysis_date)


@cli.command()
@click.option("--max-stocks", type=int, default=3, help="Maximum number of stocks to hold at once (default: 3)")
@click.option("--rebalance-interval-weeks", type=int, default=2, help="Rebalance interval in weeks (default: 2)")
@click.option("--date-start", type=str, required=True, help="Simulation start date in YYYY-MM-DD format")
@click.option("--date-end", type=str, required=True, help="Simulation end date in YYYY-MM-DD format")
def simulate(max_stocks: int, rebalance_interval_weeks: int, date_start: str, date_end: str):

    def rule_1(analysis: PriceAnalysis) -> bool:
        """Default selection criteria for simulation."""
        return (
            analysis.trend_slope_pct > 1.5
            and analysis.trend_r_squared > 0.8
            and analysis.biggest_weekly_drop_pct > -10
            and analysis.biggest_biweekly_drop_pct > -15
            and analysis.biggest_monthly_drop_pct > -15
            and analysis.change_3m_pct > 0
            and analysis.change_6m_pct > 0
            and analysis.overall_change_pct > 0
        )

    try:
        date_start_parsed = datetime.strptime(date_start, "%Y-%m-%d")
        date_end_parsed = datetime.strptime(date_end, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter("Invalid date format. Use YYYY-MM-DD format.")

    if date_start_parsed >= date_end_parsed:
        raise click.BadParameter("date_start must be before date_end")

    click.echo(f"Running simulation from {date_start_parsed.date()} to {date_end_parsed.date()}")
    click.echo(f"Max stocks: {max_stocks}, Rebalance interval: {rebalance_interval_weeks} weeks")

    symbols = stock_loader.load_sp_500()

    simulator = Simulator(
        max_stocks=max_stocks,
        rebalance_interval_weeks=rebalance_interval_weeks,
        date_start=date_start_parsed,
        date_end=date_end_parsed,
    )
    simulator.load_stock_prices(symbols)

    simulation_result = simulator.simulate(criteria=rule_1)
    click.echo(
        f"Simulation result: {simulation_result.profit_pct * 100:2.2f}%, {simulation_result.profit:2.2f}"
    )
    save_simulation_result(simulation_result, rule_1.__name__)


if __name__ == "__main__":
    cli()
