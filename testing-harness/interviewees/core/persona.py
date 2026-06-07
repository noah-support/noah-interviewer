"""Persona JSON loading and system prompt assembly for the interviewee harness."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from interviewees.core.behavior import BEHAVIORAL_BLOCK
from interviewees.core.persona_schema import GeneratedPersona, Process
from interviewees.persona_layout import PERSONA_JSON_FILENAME

DEFAULT_PROJECT = "output-test"


class Persona(BaseModel):
    """Runtime persona for a harness interview (metadata + profile fields)."""

    id: str
    project: str
    subject_label: str
    name: str
    role: str
    backstory: str
    processes: list[Process]

    @classmethod
    def from_generated(
        cls,
        profile: GeneratedPersona,
        *,
        subject_label: str,
        project: str = DEFAULT_PROJECT,
    ) -> Persona:
        return cls(
            id=f"{project}__{subject_label}",
            project=project,
            subject_label=subject_label,
            name=profile.name,
            role=profile.role,
            backstory=profile.backstory,
            processes=profile.processes,
        )


def _infer_subject_label(path: Path) -> str:
    if path.name == PERSONA_JSON_FILENAME:
        return path.parent.name
    return path.stem


def load_persona(
    path: str | Path,
    *,
    subject_label: str | None = None,
    project: str = DEFAULT_PROJECT,
) -> Persona:
    """Load and validate a persona.json file."""
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise ValueError(f"Persona file must be JSON (.json): {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Persona file must be a JSON object: {path}")

    profile = GeneratedPersona.model_validate(data)
    label = subject_label or _infer_subject_label(path)
    return Persona.from_generated(profile, subject_label=label, project=project)


def _format_process(proc: Process) -> str:
    lines = [f"Process you work on: {proc.process_name}"]
    lines.append(
        "Your steps in this process (speak about these naturally when asked; "
        "do not recite as a list unless asked to walk through the flow):"
    )
    for step in proc.steps:
        tools = (
            ", ".join(step.software_tools_used)
            if step.software_tools_used
            else "no specific tool"
        )
        handoff = (
            step.handoff_to
            if step.handoff_to
            else "you finish here / no handoff"
        )
        lines.append(
            f"- {step.step_name} (tools: {tools}; about {step.time_needed}; "
            f"then: {handoff})"
        )
    lines.append("Problems you see and how you handle them:")
    for ex in proc.exceptions:
        lines.append(
            f"- {ex.what_goes_wrong} — {ex.impact}; you recover by: {ex.recovery}"
        )
    return "\n".join(lines)


def assemble_system_prompt(persona: Persona) -> str:
    """Build the interviewee system prompt from behavior, identity, and process knowledge."""
    identity_block = (
        f"You are {persona.name}, a {persona.role}.\n\n"
        f"{persona.backstory.strip()}"
    )

    sections = [
        BEHAVIORAL_BLOCK,
        identity_block,
    ]
    for proc in persona.processes:
        sections.append(_format_process(proc))

    return "\n\n".join(sections)
