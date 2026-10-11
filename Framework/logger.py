"""
Shared logger for LoessHazardDetector.

Usage:
    from Framework.logger import get_logger
    log = get_logger(__name__)
    log.info("Loading model: %s", path)
"""

import logging
import sys

_FORMAT = "[LHD] %(message)s"

_configured = False


def _configure_root():
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger("lhd")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False
    _configured = True


def get_logger(name: str = "lhd") -> logging.Logger:
    _configure_root()
    return logging.getLogger("lhd")


def section(title: str, width: int = 58):
    """Print a section header."""
    log = get_logger()
    log.info("=" * width)
    log.info(title)
    log.info("=" * width)


def subsection(title: str, width: int = 58):
    """Print a subsection header."""
    log = get_logger()
    log.info("-" * width)
    log.info(title)
    log.info("-" * width)