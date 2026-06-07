"""Tests for premature interview close detection and BPMN close gates."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from bpmn_schema import normalize_state, unmapped_work_summary  # noqa: E402
from interview_close import (  # noqa: E402
    build_premature_close_recovery_instruction,
    can_close_interview,
    is_interviewer_closing_message,
)


def _user_state() -> dict:
    return normalize_state(
        {
            "meta": {
                "phase": "deepdive",
                "current_focus_process": "student ticket handling",
                "tangent_to_acknowledge": None,
            },
            "discovery": {
                "interviewee_role": "Process Coordinator",
                "identified_main_processes": [
                    "student ticket handling",
                    "complaint management",
                    "incident resolution",
                ],
                "is_completed": True,
            },
            "process_details": {
                "student ticket handling": {
                    "phase": "steps",
                    "steps": [
                        {
                            "step_name": "Check for any pending issues with the ticket in Sipac",
                            "tools_software_used": "Sipac",
                            "time_taken": "",
                            "handoff_to_next_actor": "",
                            "comments_to_explore": "Ask roughly how long this step takes when things go smoothly.",
                            "is_mapped": False,
                        },
                        {
                            "step_name": "Notify student about any pending issues",
                            "tools_software_used": "email",
                            "time_taken": "",
                            "handoff_to_next_actor": "",
                            "comments_to_explore": "",
                            "is_mapped": False,
                        },
                    ],
                    "exceptions": [
                        {
                            "what_goes_wrong": "Incorrect ticket information",
                            "impact": "Delays processing",
                            "recovery": "Request resubmit",
                            "comments_to_explore": "",
                            "is_mapped": True,
                        }
                    ],
                    "steps_flow_complete": False,
                    "summary_confirmed": False,
                    "is_completed": False,
                },
                "complaint management": {
                    "phase": "steps",
                    "steps": [],
                    "exceptions": [],
                    "steps_flow_complete": False,
                    "summary_confirmed": False,
                    "is_completed": False,
                },
                "incident resolution": {
                    "phase": "steps",
                    "steps": [],
                    "exceptions": [],
                    "steps_flow_complete": False,
                    "summary_confirmed": False,
                    "is_completed": False,
                },
            },
        }
    )


def test_detects_noah_closing_line():
    msg = (
        "I've covered the important parts for now, thank you, A — if you're ready, "
        "you can press the red button to end the conversation."
    )
    assert is_interviewer_closing_message(msg)


def test_cannot_close_while_deepdive_incomplete():
    state = _user_state()
    assert not can_close_interview(state)
    gaps = unmapped_work_summary(state)
    assert gaps is not None
    assert "student ticket handling" in gaps
    assert "complaint management" in gaps


def test_recovery_instruction_mentions_active_mapping():
    state = _user_state()
    recovery = build_premature_close_recovery_instruction(state)
    assert "CRITICAL CORRECTION" in recovery
    assert "student ticket handling" in recovery
    assert "how long this step takes" in recovery
