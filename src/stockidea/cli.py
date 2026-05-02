"""CLI entry point — assembles component command groups."""

import click

# Import config to initialize logging
import stockidea.config  # noqa: F401

from stockidea.datasource.cli import datasource_cli
from stockidea.indicators.cli import indicators_cli
from stockidea.backtest.cli import backtest_cli
from stockidea.agent.cli import agent_cli
from stockidea.screener.cli import screener_cli
from stockidea.telegram.cli import telegram_cli


@click.group()
def cli():
    """Stock analysis and backtest tool."""
    pass


# Register top-level commands from each component's group.
# This flattens subgroup commands so they can be called directly
# (e.g. `stockidea fetch-data` instead of `stockidea datasource fetch-data`).
for cmd_group in [
    datasource_cli,
    indicators_cli,
    backtest_cli,
    agent_cli,
    screener_cli,
]:
    for name, cmd in cmd_group.commands.items():
        cli.add_command(cmd, name)

# Telegram bot stays as a subgroup — `stockidea telegram run-bot` — since
# `run-bot` is generic enough to collide with any future module.
cli.add_command(telegram_cli)


if __name__ == "__main__":
    cli()
