"""CLI entry point — assembles component command groups."""

import click

# Import config to initialize logging
import stockidea.config  # noqa: F401

from stockidea.datasource.cli import datasource_cli
from stockidea.indicators.cli import indicators_cli
from stockidea.backtest.cli import backtest_cli
from stockidea.agent.cli import agent_cli


@click.group()
def cli():
    """Stock analysis and backtest tool."""
    pass


# Register top-level commands from each component's group.
# This flattens subgroup commands so they can be called directly
# (e.g. `stockidea fetch-data` instead of `stockidea datasource fetch-data`).
for cmd_group in [datasource_cli, indicators_cli, backtest_cli, agent_cli]:
    for name, cmd in cmd_group.commands.items():
        cli.add_command(cmd, name)


if __name__ == "__main__":
    cli()
