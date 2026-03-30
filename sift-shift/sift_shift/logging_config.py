"""
sift_shift/logging_config.py
Centralised, colourised logging setup.
"""

from __future__ import annotations

import logging
import sys


# ANSI colour codes
_RESET = "\033[0m"
_BOLD = "\033[1m"
_COLOURS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[35m",  # magenta
}


class _ColouredFormatter(logging.Formatter):
    _FMT = "{colour}{bold}[{level}]{reset}  {ts}  {msg}"

    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, "")
        ts = self.formatTime(record, "%H:%M:%S")
        return self._FMT.format(
            colour=colour,
            bold=_BOLD,
            level=record.levelname[:5],
            reset=_RESET,
            ts=ts,
            msg=record.getMessage(),
        )


def configure(level: str = "INFO") -> None:
    """Configure root logger with colourised console output."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_ColouredFormatter())
        root.addHandler(handler)
