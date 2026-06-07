"""Pydantic schema for persona.json ground-truth files."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, model_validator

_PLACEHOLDER_RE = re.compile(
    r"\b(todo|tbd|lorem|ipsum|placeholder|fixme|xxx)\b",
    re.IGNORECASE,
)


class Step(BaseModel):
    step_name: str
    software_tools_used: list[str] = Field(default_factory=list)
    time_needed: str
    handoff_to: str | None


class Exception(BaseModel):
    what_goes_wrong: str
    impact: str
    recovery: str


class Process(BaseModel):
    process_name: str
    steps: list[Step]
    exceptions: list[Exception]

    @model_validator(mode="after")
    def _non_empty_steps_and_exceptions(self) -> Process:
        if not self.steps:
            raise ValueError("each process must have at least one step")
        if not self.exceptions:
            raise ValueError("each process must have at least one exception")
        return self


class GeneratedPersona(BaseModel):
    name: str
    role: str
    backstory: str
    processes: list[Process]

    @model_validator(mode="after")
    def _validate_persona(self) -> GeneratedPersona:
        if not self.processes:
            raise ValueError("processes must be non-empty")
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.role.strip():
            raise ValueError("role must be non-empty")
        backstory = self.backstory.strip()
        if not backstory:
            raise ValueError("backstory must be non-empty")
        if _PLACEHOLDER_RE.search(backstory):
            raise ValueError("backstory must not contain placeholder text")
        return self
