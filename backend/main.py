"""
HTTP API entrypoint (FastAPI). Run the LiveKit worker separately: `python interviewer.py dev`.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv(".env.local", override=True)

from http_api import app  # noqa: E402 — ASGI app (e.g. uvicorn main:app)
from seeder import reset_and_seed  # noqa: E402


if __name__ == "__main__":
    reset_and_seed()

    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        log_level=os.getenv("API_LOG_LEVEL", "info"),
    )
