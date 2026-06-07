"""End-of-interview sentinel detection and stripping."""

from __future__ import annotations

import re

SENTINEL = "[[INTERVIEW_COMPLETE]]"

# Noah closing lines often omit the sentinel on hosted ConvAI agents.
_CLOSING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"red\s+button", re.IGNORECASE),
    re.compile(r"end\s+the\s+conversation", re.IGNORECASE),
    re.compile(r"end\s+the\s+interview", re.IGNORECASE),
    re.compile(
        r"covered\s+(?:all\s+)?(?:the\s+)?(?:important\s+)?(?:ground|topics|everything)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:thank\s+you|thanks\b).{0,500}covered.{0,120}"
        r"(?:important|everything|ground|topics)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"covered.{0,120}(?:important|everything|ground|topics).{0,500}"
        r"(?:thank\s+you|thanks\b|been\s+really\s+helpful|you(?:'ve| have)\s+been)",
        re.IGNORECASE | re.DOTALL,
    ),
)


def contains_sentinel(text: str) -> bool:
    """Return True if the exact sentinel substring is present."""
    return SENTINEL in text


def is_interviewer_closing_message(text: str) -> bool:
    """
    True when the interviewer is clearly ending the interview (Noah-style close).

    Used when ``[[INTERVIEW_COMPLETE]]`` is missing from hosted agents.
    """
    if not (text or "").strip():
        return False
    if contains_sentinel(text):
        return True
    return any(p.search(text) for p in _CLOSING_PATTERNS)


def strip_sentinel(text: str) -> str:
    """Remove all sentinel occurrences and trim surrounding whitespace."""
    return text.replace(SENTINEL, "").strip()


def ended_by_for_disconnect(raw_interviewer_text: str) -> str:
    """Classify why the harness is disconnecting after an interviewer turn."""
    if contains_sentinel(raw_interviewer_text):
        return "sentinel"
    if is_interviewer_closing_message(raw_interviewer_text):
        return "closing"
    return "turn_cap"
