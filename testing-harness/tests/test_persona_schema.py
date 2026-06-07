import pytest
from pydantic import ValidationError

from interviewees.core.persona_schema import Exception, GeneratedPersona, Process, Step


def _minimal_persona_dict() -> dict:
    return {
        "name": "Alex Rivera",
        "role": "Service Coordinator",
        "backstory": (
            "Alex has worked in student services for four years. "
            "They handle intake tickets and coordinate with academic staff. "
            "Most days involve Sipac and email follow-ups. "
            "They prefer clear handoffs before closing a case."
        ),
        "processes": [
            {
                "process_name": "Ticket handling",
                "steps": [
                    {
                        "step_name": "Open ticket",
                        "software_tools_used": ["Sipac"],
                        "time_needed": "10 minutes",
                        "handoff_to": "Coordination",
                    },
                    {
                        "step_name": "Close ticket",
                        "software_tools_used": [],
                        "time_needed": "5 minutes",
                        "handoff_to": None,
                    },
                ],
                "exceptions": [
                    {
                        "what_goes_wrong": "Sipac is down",
                        "impact": "Cannot log the request",
                        "recovery": "Use the backup spreadsheet and sync later",
                    }
                ],
            }
        ],
    }


def test_valid_minimal_persona() -> None:
    persona = GeneratedPersona.model_validate(_minimal_persona_dict())
    assert persona.name == "Alex Rivera"
    assert len(persona.processes) == 1
    assert persona.processes[0].steps[-1].handoff_to is None


def test_rejects_empty_processes() -> None:
    data = _minimal_persona_dict()
    data["processes"] = []
    with pytest.raises(ValidationError, match="processes"):
        GeneratedPersona.model_validate(data)


def test_rejects_empty_steps() -> None:
    data = _minimal_persona_dict()
    data["processes"][0]["steps"] = []
    with pytest.raises(ValidationError, match="at least one step"):
        GeneratedPersona.model_validate(data)


def test_rejects_empty_exceptions() -> None:
    data = _minimal_persona_dict()
    data["processes"][0]["exceptions"] = []
    with pytest.raises(ValidationError, match="at least one exception"):
        GeneratedPersona.model_validate(data)


def test_rejects_placeholder_backstory() -> None:
    data = _minimal_persona_dict()
    data["backstory"] = "TODO fill this in later."
    with pytest.raises(ValidationError, match="placeholder"):
        GeneratedPersona.model_validate(data)


def test_step_handoff_to_nullable() -> None:
    step = Step.model_validate(
        {
            "step_name": "Finish",
            "software_tools_used": [],
            "time_needed": "1 hour",
            "handoff_to": None,
        }
    )
    assert step.handoff_to is None


def test_exception_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        Exception.model_validate(
            {"what_goes_wrong": "x", "impact": "y"}
        )
