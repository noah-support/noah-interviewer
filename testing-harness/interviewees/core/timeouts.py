"""Shared timeout helpers for transport clients."""

from __future__ import annotations

import os

from interviewees.env import load_harness_env


def interviewer_idle_timeout_s() -> float:
    """Max seconds to wait for the next interviewer message before ending."""
    load_harness_env()
    raw = (os.environ.get("INTERVIEWER_IDLE_TIMEOUT_S") or "600").strip()
    try:
        return max(30.0, float(raw))
    except ValueError:
        return 180.0


def interviewee_reply_delay_s() -> float:
    """Pause after each interviewer message before the interviewee replies (AI-to-AI pacing)."""
    load_harness_env()
    raw = (os.environ.get("INTERVIEWEE_REPLY_DELAY_S") or "2.5").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 2.5

