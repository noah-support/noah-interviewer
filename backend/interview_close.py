"""Detect premature interview closing and build recovery instructions from BPMN state."""

from __future__ import annotations

import re
from typing import Any

from bpmn_schema import (
    PHASE_ROUNDUP,
    first_active_exception,
    first_active_step,
    first_incomplete_process_name,
    incomplete_process_names,
    meta_phase,
    process_ready_for_confirm,
    process_ready_for_exceptions,
    step_gap_comment,
    step_is_fully_mapped,
    unmapped_work_summary,
)

SENTINEL = "[[INTERVIEW_COMPLETE]]"

_CLOSING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"red\s+button", re.IGNORECASE),
    re.compile(r"end\s+the\s+conversation", re.IGNORECASE),
    re.compile(r"end\s+the\s+interview", re.IGNORECASE),
    re.compile(
        r"covered\s+(?:all\s+)?(?:the\s+)?(?:important\s+)?(?:ground|topics|everything|parts)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:thank\s+you|thanks\b).{0,500}covered.{0,120}"
        r"(?:important|everything|ground|topics|parts)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"covered.{0,120}(?:important|everything|ground|topics|parts).{0,500}"
        r"(?:thank\s+you|thanks\b|been\s+really\s+helpful|you(?:'ve| have)\s+been)",
        re.IGNORECASE | re.DOTALL,
    ),
)


def is_interviewer_closing_message(text: str) -> bool:
    """True when the assistant is clearly trying to end the interview."""
    if not (text or "").strip():
        return False
    if SENTINEL in text:
        return True
    return any(p.search(text) for p in _CLOSING_PATTERNS)


def can_close_interview(state: dict[str, Any]) -> bool:
    """Closing is allowed only in roundup after every process is fully mapped."""
    if meta_phase(state) != PHASE_ROUNDUP:
        return False
    return not incomplete_process_names(state)


def build_premature_close_recovery_instruction(state: dict[str, Any]) -> str:
    """
    Verbatim instructions for a regeneration turn after a blocked closing attempt.
    """
    phase = meta_phase(state)
    gaps = unmapped_work_summary(state) or "process details still incomplete in state"
    focus = first_incomplete_process_name(state) or "the current process"
    pd = state.get("process_details") if isinstance(state.get("process_details"), dict) else {}
    proc = pd.get(focus) if isinstance(pd.get(focus), dict) else {}

    next_question = ""
    active_step, _ = first_active_step(proc)
    if active_step:
        next_question = (
            step_gap_comment(active_step)
            or (active_step.get("comments_to_explore") or "").strip()
        )
    if not next_question:
        active_exc, _ = first_active_exception(proc)
        if active_exc:
            next_question = (active_exc.get("comments_to_explore") or "").strip()
    if not next_question and not (proc.get("steps") if isinstance(proc.get("steps"), list) else []):
        next_question = (
            f"Ask how they usually carry out '{focus}' — what happens first and what tools they use."
        )
    elif not next_question and not process_ready_for_exceptions(proc):
        next_question = (
            "Ask what happens next in the workflow after the last handoff you mapped."
        )
    elif not next_question and process_ready_for_exceptions(proc) and not process_ready_for_confirm(
        proc
    ):
        next_question = "Ask what tends to go wrong in this process — one concrete failure scenario."
    elif not next_question and process_ready_for_confirm(proc):
        next_question = (
            f"Briefly summarize how '{focus}' works and ask if you understood correctly."
        )

    question_hint = next_question or "Ask one concrete mapping question from dynamic working memory."

    return (
        "CRITICAL CORRECTION: Your previous reply wrongly tried to end the interview. "
        f"meta.phase is {phase!r} — closing is NOT allowed. "
        f"State still requires: {gaps}. "
        "Do NOT thank them for finishing, say you covered everything, mention the red button, "
        "or append [[INTERVIEW_COMPLETE]]. "
        "Give at most one short acknowledgement, then ask exactly ONE follow-up question. "
        f"Focus on '{focus}'. {question_hint}"
    )
