"""Persona YAML loading and system prompt assembly."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from interviewees.core.behavior import BEHAVIORAL_BLOCK


class Identity(BaseModel):
    name: str
    role: str
    company: str
    department: str
    years_in_role: int


class Personality(BaseModel):
    tone: str
    quirks: list[str] = Field(default_factory=list)


class Knowledge(BaseModel):
    what_i_do: str
    what_i_receive: str
    what_i_hand_off: str
    decision_points: str
    exceptions_and_edge_cases: str
    things_i_only_hear_about: str = ""


class Persona(BaseModel):
    id: str
    project: str
    subject_label: str
    identity: Identity
    personality: Personality
    knowledge: Knowledge


def load_persona(path: str | Path) -> Persona:
    """Load and validate a persona YAML file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Persona file must be a YAML mapping: {path}")
    return Persona.model_validate(data)


def _render_quirks(quirks: list[str]) -> str:
    if not quirks:
        return ""
    if len(quirks) == 1:
        return quirks[0]
    return " ".join(quirks)


def assemble_system_prompt(persona: Persona) -> str:
    """Build the interviewee system prompt from behavior, identity, and knowledge."""
    identity = persona.identity
    personality = persona.personality
    knowledge = persona.knowledge

    quirks_text = _render_quirks(personality.quirks)
    quirks_block = f"\n{quirks_text}" if quirks_text else ""

    identity_block = (
        f"You are {identity.name}, a {identity.role} at {identity.company} "
        f"in the {identity.department} department. "
        f"You have been in this role for {identity.years_in_role} years.\n\n"
        f"Tone: {personality.tone}.{quirks_block}"
    )

    sections = [
        BEHAVIORAL_BLOCK,
        identity_block,
        f"What you do day to day:\n{knowledge.what_i_do.strip()}",
        f"Where work comes to you from:\n{knowledge.what_i_receive.strip()}",
        f"Where work goes after you:\n{knowledge.what_i_hand_off.strip()}",
        f"Decisions you make:\n{knowledge.decision_points.strip()}",
        (
            "Things that go wrong and how you handle them:\n"
            f"{knowledge.exceptions_and_edge_cases.strip()}"
        ),
    ]

    secondhand = (knowledge.things_i_only_hear_about or "").strip()
    if secondhand:
        sections.append(
            "Things you only hear about secondhand (don't volunteer these, "
            "only mention if directly asked, and be vague):\n"
            f"{secondhand}"
        )

    return "\n\n".join(sections)
