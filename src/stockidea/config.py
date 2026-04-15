"""Logging configuration. Import this module to initialize logging."""

import logging
import os
import sys

# Force unbuffered output BEFORE anything else
os.environ["PYTHONUNBUFFERED"] = "1"
# Reopen stderr as unbuffered
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)


class FlushHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application."""
    handler = FlushHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.root.handlers = []
    logging.root.addHandler(handler)
    logging.root.setLevel(level)


# Initialize logging on module import
setup_logging()
