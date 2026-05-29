from pathlib import Path

import pytest

from interviewees.core.persona import assemble_system_prompt, load_persona

FIXTURE = Path(__file__).parent / "fixtures" / "sample_persona.yaml"


def test_load_and_assemble_contains_all_sections():
    persona = load_persona(FIXTURE)
    prompt = assemble_system_prompt(persona)

    assert "You are being interviewed by a colleague" in prompt
    assert "You are Marta, a Repair Coordinator" in prompt
    assert "Tone: friendly but a bit rushed" in prompt
    assert "Tom" in prompt
    assert "What you do day to day:" in prompt
    assert "Where work comes to you from:" in prompt
    assert "Where work goes after you:" in prompt
    assert "Decisions you make:" in prompt
    assert "Things that go wrong and how you handle them:" in prompt
    assert "Things you only hear about secondhand" in prompt


def test_load_invalid_yaml_raises():
    with pytest.raises(Exception):
        load_persona(Path(__file__).parent / "fixtures" / "nonexistent.yaml")
