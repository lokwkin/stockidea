"""CLI for the Telegram bot module."""

import click

from stockidea.telegram import service as telegram_service


@click.group("telegram")
def telegram_cli():
    """Telegram bot commands."""
    pass


@telegram_cli.command("run-bot", help="Start the Telegram bot (long-running).")
def run_bot_cmd() -> None:
    telegram_service.run_bot()
