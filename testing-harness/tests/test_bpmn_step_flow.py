"""Tests for backend step-flow gates (non-terminal handoff → more steps)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from bpmn_schema import (  # noqa: E402
    enforce_process_steps,
    is_terminal_handoff,
    process_needs_more_steps,
    process_ready_for_confirm,
    process_ready_for_exceptions,
)


def _one_step_process(handoff: str = "CRA Team") -> dict:
    return enforce_process_steps(
        {
            "phase": "confirm",
            "steps": [
                {
                    "step_name": "Student opens ticket",
                    "tools_software_used": "Sipac",
                    "time_taken": "15 minutes",
                    "handoff_to_next_actor": handoff,
                    "comments_to_explore": "",
                    "is_mapped": True,
                }
            ],
            "exceptions": [
                {
                    "what_goes_wrong": "Incorrect ticket information",
                    "impact": "Delays",
                    "recovery": "Ask student to resubmit",
                    "comments_to_explore": "",
                    "is_mapped": True,
                }
            ],
            "summary_confirmed": True,
            "is_completed": True,
        }
    )


def test_non_terminal_handoff_requires_more_steps():
    proc = _one_step_process("CRA Team")
    assert process_needs_more_steps(proc)
    assert not process_ready_for_exceptions(proc)
    assert not process_ready_for_confirm(proc)
    assert proc["phase"] == "steps"
    assert proc["summary_confirmed"] is False
    assert proc["is_completed"] is False
    assert len(proc["steps"]) >= 2


def test_terminal_handoff_allows_exceptions_phase():
    proc = _one_step_process("none")
    assert not process_needs_more_steps(proc)
    assert process_ready_for_exceptions(proc)


def test_steps_flow_complete_overrides_handoff():
    proc = _one_step_process("CRA Team")
    proc["steps_flow_complete"] = True
    proc = enforce_process_steps(proc)
    assert not process_needs_more_steps(proc)


def test_is_terminal_handoff():
    assert is_terminal_handoff("none")
    assert is_terminal_handoff("")
    assert not is_terminal_handoff("CRA Team")
