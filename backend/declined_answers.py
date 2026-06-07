"""Detect when the interviewee cannot answer and stop re-asking the same gap."""

from __future__ import annotations

import copy
import re
from typing import Any

from bpmn_schema import (
    EXCEPTION_REQUIRED_FIELDS,
    PHASE_DEEPDIVE,
    STEP_REQUIRED_FIELDS,
    _normalize_exception,
    _normalize_step,
    enforce_process_steps,
    enforce_steps_on_state,
    exception_missing_fields,
    first_active_exception,
    first_active_step,
    meta_phase,
    resolve_focus_process_name,
    step_missing_fields,
)

UNKNOWN_TO_INTERVIEWEE = "unknown to interviewee"

_DECLINE_PHRASES: tuple[str, ...] = (
    "don't have",
    "do not have",
    "don't know",
    "do not know",
    "not able to",
    "unable to",
    "can't provide",
    "cannot provide",
    "can't answer",
    "cannot answer",
    "i'm not sure",
    "i am not sure",
    "no idea",
    "would need to check",
    "you'd need to check",
    "you would need to check",
    "need to check with",
    "ask the ",
    "check with the",
    "check with ",
    "not on my side",
    "outside my",
    "don't handle that",
    "do not handle that",
    "that's more on",
    "that is more on",
    "someone else",
    "another team",
    "not my area",
    "not in my",
    "sorry, but i don't",
    "sorry but i don't",
    "doesn't have the information",
    "does not have the information",
)

_TIME_QUESTION = (
    "how long",
    "how much time",
    "duration",
    "estimate",
    "roughly how",
    "takes on their side",
    "on their side",
    "minutes",
    "hours",
    "days",
)

_TOOL_QUESTION = ("tool", "software", "system", "which app", "what do you use")

_HANDOFF_QUESTION = (
    "hand off",
    "handoff",
    "hand this",
    "who receives",
    "who do you pass",
    "next person",
    "next team",
    "on their side",
)

_STEP_NAME_QUESTION = ("what happens", "what do you call", "name this", "describe this step")

_EXCEPTION_IMPACT = ("impact", "how often", "delay", "slow down")
_EXCEPTION_RECOVERY = ("recover", "fix", "work around", "what do you do when")


def user_declined_to_answer(text: str) -> bool:
    """True when the interviewee indicates they lack this information."""
    t = (text or "").strip().lower()
    if not t:
        return False
    return any(phrase in t for phrase in _DECLINE_PHRASES)


def infer_field_from_interviewer_question(
    assistant_text: str,
    missing_fields: list[str],
) -> str | None:
    """Map the interviewer's last question to a missing required field."""
    if not missing_fields:
        return None
    a = (assistant_text or "").strip().lower()
    if not a:
        return missing_fields[0]

    checks: list[tuple[str, tuple[str, ...]]] = [
        ("time_taken", _TIME_QUESTION),
        ("tools_software_used", _TOOL_QUESTION),
        ("handoff_to_next_actor", _HANDOFF_QUESTION),
        ("step_name", _STEP_NAME_QUESTION),
        ("impact", _EXCEPTION_IMPACT),
        ("recovery", _EXCEPTION_RECOVERY),
        ("what_goes_wrong", ("go wrong", "goes wrong", "problem", "issue", "stuck")),
    ]
    for field, cues in checks:
        if field in missing_fields and any(cue in a for cue in cues):
            return field
    return missing_fields[0]


def unavailable_value_for_field(field: str, user_text: str) -> str:
    """Canonical English value stored in state when the interviewee cannot answer."""
    note = _referral_note(user_text)
    if field == "time_taken":
        return f"{UNKNOWN_TO_INTERVIEWEE}{note}"
    if field == "tools_software_used":
        return f"{UNKNOWN_TO_INTERVIEWEE}{note}"
    if field == "handoff_to_next_actor":
        return f"{UNKNOWN_TO_INTERVIEWEE}{note}"
    if field == "step_name":
        return f"{UNKNOWN_TO_INTERVIEWEE}{note}"
    if field in EXCEPTION_REQUIRED_FIELDS:
        return f"{UNKNOWN_TO_INTERVIEWEE}{note}"
    return UNKNOWN_TO_INTERVIEWEE


def _referral_note(user_text: str) -> str:
    """Optional hint when they name another team to ask."""
    t = user_text or ""
    m = re.search(
        r"(?:check with|ask(?:\s+the)?)\s+(?:the\s+)?([A-Z][A-Za-z0-9 &/-]{2,40}(?:Team|team)?)",
        t,
    )
    if m:
        return f" (refer to {m.group(1).strip()})"
    return ""


def _normalize_compare(text: str) -> str:
    return re.sub(r"[^\w\s]", "", (text or "").lower()).strip()


def questions_are_near_duplicate(previous: str, new: str) -> bool:
    """True when the assistant is effectively repeating the same question."""
    a = _normalize_compare(previous)
    b = _normalize_compare(new)
    if not a or not b:
        return False
    if a == b:
        return True
    wa, wb = set(a.split()), set(b.split())
    if len(wa) < 5:
        return a in b or b in a
    overlap = len(wa & wb) / max(len(wa), 1)
    return overlap >= 0.82


def reply_reasks_after_decline(
    *,
    previous_assistant: str,
    new_assistant: str,
    user_text: str,
    missing_fields: list[str],
) -> bool:
    if not user_declined_to_answer(user_text):
        return False
    if questions_are_near_duplicate(previous_assistant, new_assistant):
        return True
    field = infer_field_from_interviewer_question(previous_assistant, missing_fields)
    if not field:
        return False
    return (
        infer_field_from_interviewer_question(new_assistant, [field]) == field
        or questions_are_near_duplicate(previous_assistant, new_assistant)
    )


def apply_declined_fields_from_transcript(
    transcript: list[dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    When the user says they cannot answer, fill the targeted gap so mapping advances.
    """
    if meta_phase(state) != PHASE_DEEPDIVE:
        return state

    out = copy.deepcopy(state)
    pd = out.get("process_details")
    if not isinstance(pd, dict):
        return out

    focus = resolve_focus_process_name(out, prefer_tracker_focus=True)
    if not focus:
        return out

    proc = pd.get(focus)
    if not isinstance(proc, dict):
        return out

    changed = False
    for i, line in enumerate(transcript):
        if line.get("role") != "user":
            continue
        user_text = (line.get("content") or "").strip()
        if not user_declined_to_answer(user_text):
            continue

        asst_text = ""
        for j in range(i - 1, -1, -1):
            if transcript[j].get("role") == "assistant":
                asst_text = (transcript[j].get("content") or "").strip()
                break
        if not asst_text:
            continue

        active_step, step_idx = first_active_step(proc)
        if active_step is not None and step_idx is not None:
            missing = step_missing_fields(active_step)
            field = infer_field_from_interviewer_question(asst_text, missing)
            if field:
                steps = proc.get("steps")
                if isinstance(steps, list) and 0 <= step_idx < len(steps):
                    step = _normalize_step(steps[step_idx] if isinstance(steps[step_idx], dict) else {})
                    if not (step.get(field) or "").strip():
                        step[field] = unavailable_value_for_field(field, user_text)
                        step["comments_to_explore"] = ""
                        steps[step_idx] = step
                        changed = True

        active_exc, exc_idx = first_active_exception(proc)
        if active_exc is not None and exc_idx is not None:
            missing_exc = exception_missing_fields(active_exc)
            field = infer_field_from_interviewer_question(asst_text, missing_exc)
            if field:
                excs = proc.get("exceptions")
                if isinstance(excs, list) and 0 <= exc_idx < len(excs):
                    exc = _normalize_exception(
                        excs[exc_idx] if isinstance(excs[exc_idx], dict) else {}
                    )
                    if not (exc.get(field) or "").strip():
                        exc[field] = unavailable_value_for_field(field, user_text)
                        exc["comments_to_explore"] = ""
                        excs[exc_idx] = exc
                        changed = True

    if not changed:
        return out

    pd[focus] = enforce_process_steps(proc)
    out["process_details"] = pd
    return enforce_steps_on_state(out)


def build_repeat_question_recovery_instruction(
    state: dict[str, Any],
    *,
    user_text: str,
) -> str:
    """Instructions when the model repeated a question after a decline."""
    from interview_close import build_premature_close_recovery_instruction

    base = (
        "CRITICAL: The interviewee already said they do not have this information. "
        "Do NOT ask the same question again or press for an estimate. "
        "Acknowledge briefly (e.g. that is fine — you will note it is outside their scope), "
        "then ask exactly ONE different mapping question — the next item from dynamic working memory. "
    )
    if user_declined_to_answer(user_text):
        referral = _referral_note(user_text).strip()
        if referral:
            base += f"They referred you{referral}; you may accept that and move on. "
    next_q = build_premature_close_recovery_instruction(state)
    if "Focus on" in next_q:
        tail = next_q.split("Focus on", 1)[-1]
        base += f"Focus on{tail}"
    return base
