"""Load optional local env file without overriding platform-injected variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent


def load_app_env() -> None:
    env_file = os.getenv("ENV_FILE", str(_BACKEND_DIR / ".env.local"))
    if Path(env_file).is_file():
        load_dotenv(env_file, override=False)
