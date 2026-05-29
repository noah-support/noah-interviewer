"""End-of-interview sentinel detection and stripping."""

SENTINEL = "[[INTERVIEW_COMPLETE]]"


def contains_sentinel(text: str) -> bool:
    """Return True if the exact sentinel substring is present."""
    return SENTINEL in text


def strip_sentinel(text: str) -> str:
    """Remove all sentinel occurrences and trim surrounding whitespace."""
    return text.replace(SENTINEL, "").strip()
