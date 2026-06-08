"""Shared logging setup for harness CLI and transport clients."""

from __future__ import annotations

import logging
import os
import sys


def configure_harness_logging(*, verbose: bool = False) -> None:
    level_name = (os.environ.get("HARNESS_LOG_LEVEL") or "").strip().upper()
    if level_name:
        level = getattr(logging, level_name, logging.INFO)
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    for name in ("harness", "harness.evaluation"):
        log = logging.getLogger(name)
        if log.handlers:
            log.handlers.clear()
        log.addHandler(handler)
        log.setLevel(level)
        log.propagate = False
