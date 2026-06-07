"""Schema for reconstruction output (strict extraction, sparse fields)."""

from __future__ import annotations

from interviewees.core.persona_schema import Exception, Step
from pydantic import BaseModel, Field


class ReconstructedProcess(BaseModel):
    """Process entry; steps/exceptions may be empty when not discussed."""

    process_name: str = ""
    steps: list[Step] = Field(default_factory=list)
    exceptions: list[Exception] = Field(default_factory=list)


class ReconstructedPersona(BaseModel):
    name: str = ""
    role: str = ""
    processes: list[ReconstructedProcess] = Field(default_factory=list)


class GroundTruthProfile(BaseModel):
    """persona.json without backstory — used for validation only."""

    name: str
    role: str
    processes: list[ReconstructedProcess]
