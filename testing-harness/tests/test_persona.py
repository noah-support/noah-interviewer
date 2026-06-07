from pathlib import Path

import pytest

from interviewees.core.persona import assemble_system_prompt, load_persona

FIXTURE = Path(__file__).parent / "fixtures" / "sample_persona.json"


def test_load_and_assemble_contains_all_sections():
    persona = load_persona(FIXTURE, subject_label="S0", project="ComputerRepair_1")
    prompt = assemble_system_prompt(persona)

    assert "You are being interviewed by a colleague" in prompt
    assert "You are Marta, a Repair Coordinator" in prompt
    assert "Northwind" in prompt or "workshop" in prompt
    assert "Tom" in prompt
    assert "Process you work on: Computer repair intake" in prompt
    assert "Review intake from front desk" in prompt
    assert "Parts are back-ordered" in prompt
    assert persona.id == "ComputerRepair_1__S0"


def test_load_invalid_json_raises():
    with pytest.raises(Exception):
        load_persona(Path(__file__).parent / "fixtures" / "nonexistent.json")


def test_load_rejects_yaml():
    with pytest.raises(ValueError, match="JSON"):
        load_persona(Path(__file__).parent / "fixtures" / "sample_persona.yaml")
