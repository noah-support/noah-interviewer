"""Tests for interviewee 'don't know' handling and repeat-question guard."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from bpmn_schema import enforce_process_steps, normalize_state  # noqa: E402
from declined_answers import (  # noqa: E402
    apply_declined_fields_from_transcript,
    questions_are_near_duplicate,
    reply_reasks_after_decline,
    user_declined_to_answer,
)


def _handoff_step_state() -> dict:
    return normalize_state(
        {
            "meta": {
                "phase": "deepdive",
                "current_focus_process": "student ticket handling",
                "tangent_to_acknowledge": None,
            },
            "discovery": {
                "interviewee_role": "Coordinator",
                "identified_main_processes": ["student ticket handling"],
                "is_completed": True,
            },
            "process_details": {
                "student ticket handling": enforce_process_steps(
                    {
                        "phase": "steps",
                        "steps": [
                            {
                                "step_name": "Notify Approval Team",
                                "tools_software_used": "none",
                                "time_taken": "n/a",
                                "handoff_to_next_actor": "Approval Team",
                                "comments_to_explore": "",
                                "is_mapped": True,
                            },
                            {
                                "step_name": "Approval Team processes handoff",
                                "tools_software_used": "unknown",
                                "time_taken": "",
                                "handoff_to_next_actor": "",
                                "comments_to_explore": "",
                                "is_mapped": False,
                            },
                        ],
                        "exceptions": [],
                        "steps_flow_complete": False,
                        "summary_confirmed": False,
                        "is_completed": False,
                    }
                ),
            },
        }
    )


def test_user_declined_phrases():
    assert user_declined_to_answer(
        "I'm not able to provide an estimate for that handoff. You'd need to check with the Approval Team."
    )
    assert user_declined_to_answer(
        "I don't have the information to provide an estimate for the handoff duration on their side."
    )


def test_apply_declined_fills_time_taken():
    state = _handoff_step_state()
    transcript = [
        {
            "role": "assistant",
            "content": "Could you estimate roughly how long that handoff takes on their side?",
        },
        {
            "role": "user",
            "content": (
                "I'm not able to provide an estimate for that handoff. "
                "You'd need to check with the Approval Team for the specifics."
            ),
        },
    ]
    updated = apply_declined_fields_from_transcript(transcript, state)
    steps = updated["process_details"]["student ticket handling"]["steps"]
    pending = [s for s in steps if not (s.get("time_taken") or "").strip()]
    assert not pending
    assert "unknown to interviewee" in steps[-1]["time_taken"].lower()


def test_repeat_question_detection():
    prev = "Could you estimate roughly how long that handoff takes on their side?"
    new = "Could you estimate roughly how long that handoff takes on their side?"
    user = (
        "I don't have the information to provide an estimate for the handoff duration on their side. "
        "You'd need to ask the Approval Team for that detail."
    )
    assert questions_are_near_duplicate(prev, new)
    assert reply_reasks_after_decline(
        previous_assistant=prev,
        new_assistant=new,
        user_text=user,
        missing_fields=["time_taken"],
    )
