"""Load testing-harness/.env for all harness scripts and libraries."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_loaded = False


def harness_root() -> Path:
    """Directory containing runner.py, personas/, and .env."""
    return Path(__file__).resolve().parents[1]


def load_harness_env(*, override: bool = False) -> Path:
    """
    Load ``testing-harness/.env`` into ``os.environ`` via python-dotenv.

    Idempotent: later calls are no-ops unless ``override=True``.
    Existing process env vars win when ``override=False`` (dotenv default).
    """
    global _loaded
    env_path = harness_root() / ".env"
    if _loaded and not override:
        return env_path
    load_dotenv(env_path, override=override)
    _loaded = True
    return env_path


def require_env(name: str) -> str:
    """Return a non-empty env var after ensuring .env has been loaded."""
    load_harness_env()
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is not set. Add it to {harness_root() / '.env'} "
            f"(see config.example.env)."
        )
    return value
