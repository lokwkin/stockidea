"""CLI commands for stockpick using Click."""

import click
from datetime import datetime

from stockpick import data_loader
from stockpick.analysis import analysis
from stockpick.rule_engine import compile_rule

from dotenv import load_dotenv

from stockpick.simulation.simulator import Simulator, save_simulation_result

load_dotenv()


@click.group()
def cli():
    """Stock analysis and simulation tool."""
    pass


@cli.command("analyze", help="Analyze stock prices for a given date")
@click.option("--date", "-d", type=str, required=False, default=datetime.now().strftime("%Y-%m-%d"), help="Analysis date in YYYY-MM-DD format")
def analyze(date: str):
    try:
        analysis_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {date}. Use YYYY-MM-DD format.")

    symbols = data_loader.load_sp_500()

    stock_prices = data_loader.fetch_stock_prices_batch(symbols)

    analysis.analyze_stock_batch(stock_prices=stock_prices, analysis_date=analysis_date, back_period_weeks=52)


@cli.command("pick", help="Apply a rule onto analyzed stock prices for a given date range.")
@click.option("--date", "-d", type=str, required=False, default=datetime.now().strftime("%Y-%m-%d"), help="Analysis date in YYYY-MM-DD format")
@click.option("--rule", "-r", type=str, required=True, help="Rule expression string (e.g., 'change_3m_pct > 10 AND biggest_biweekly_drop_pct > 15')")
def pick(date: str, rule: str):
    try:
        analysis_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter("Invalid date format. Use YYYY-MM-DD format.")

    # Compile the rule
    try:
        rule_func = compile_rule(rule)
    except Exception as e:
        raise click.BadParameter(f"Invalid rule expression: {e}")

    symbols = data_loader.load_sp_500()

    stock_prices = data_loader.fetch_stock_prices_batch(symbols)
    analyses, _ = analysis.analyze_stock_batch(
        stock_prices=stock_prices, analysis_date=analysis_date, back_period_weeks=52)
    selected_stocks = analysis.apply_rule(analyses=analyses, max_stocks=3, rule_func=rule_func)
    return selected_stocks


@cli.command("simulate", help="Simulate investment strategy for a given date range.")
@click.option("--max-stocks", type=int, default=3, help="Maximum number of stocks to hold at once (default: 3)")
@click.option("--rebalance-interval-weeks", type=int, default=2, help="Rebalance interval in weeks (default: 2)")
@click.option("--date-start", type=str, required=True, help="Simulation start date in YYYY-MM-DD format")
@click.option("--date-end", type=str, required=True, help="Simulation end date in YYYY-MM-DD format")
@click.option(
    "--rule", "-r",
    type=str,
    help="Rule expression string (e.g., 'change_3m_pct > 10 AND biggest_biweekly_drop_pct > 15')",
)
def simulate(max_stocks: int, rebalance_interval_weeks: int, date_start: str, date_end: str, rule: str):
    try:
        date_start_parsed = datetime.strptime(date_start, "%Y-%m-%d")
        date_end_parsed = datetime.strptime(date_end, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter("Invalid date format. Use YYYY-MM-DD format.")

    if date_start_parsed >= date_end_parsed:
        raise click.BadParameter("date_start must be before date_end")

    # Compile the rule
    try:
        rule_func = compile_rule(rule)
    except Exception as e:
        raise click.BadParameter(f"Invalid rule expression: {e}")

    click.echo(f"Running simulation from {date_start_parsed.date()} to {date_end_parsed.date()}")
    click.echo(f"Max stocks: {max_stocks}, Rebalance interval: {rebalance_interval_weeks} weeks")
    click.echo(f"Rule: {rule}")

    symbols = data_loader.load_sp_500()

    simulator = Simulator(
        max_stocks=max_stocks,
        rebalance_interval_weeks=rebalance_interval_weeks,
        date_start=date_start_parsed,
        date_end=date_end_parsed,
        rule_func=rule_func,
        rule_raw=rule,
    )
    simulator.load_stock_prices(symbols)

    simulation_result = simulator.simulate()
    click.echo(
        f"Simulation result: {simulation_result.profit_pct * 100:2.2f}%, {simulation_result.profit:2.2f}"
    )
    save_simulation_result(simulation_result)


if __name__ == "__main__":
    cli()
