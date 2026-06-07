"""Flatten persona profiles to embeddable field texts."""

from __future__ import annotations

from dataclasses import dataclass

from interviewees.evaluation.reconstructed_schema import (
    GroundTruthProfile,
    ReconstructedPersona,
    ReconstructedProcess,
)


@dataclass(frozen=True)
class FieldText:
    path: str
    text: str


def _step_composite(step) -> str:
    tools = ", ".join(step.software_tools_used) if step.software_tools_used else ""
    handoff = step.handoff_to if step.handoff_to is not None else ""
    return f"{step.step_name} | tools: {tools} | time: {step.time_needed} | handoff: {handoff}"


def _exception_composite(exc) -> str:
    return f"{exc.what_goes_wrong} | {exc.impact} | {exc.recovery}"


def flatten_profile(profile: GroundTruthProfile | ReconstructedPersona) -> list[FieldText]:
    fields: list[FieldText] = [
        FieldText("name", profile.name or ""),
        FieldText("role", profile.role or ""),
    ]
    for pi, proc in enumerate(profile.processes):
        prefix = f"processes[{pi}]"
        fields.append(FieldText(f"{prefix}.process_name", proc.process_name or ""))
        for si, step in enumerate(proc.steps):
            sp = f"{prefix}.steps[{si}]"
            fields.append(FieldText(f"{sp}.step_name", step.step_name or ""))
            tools = ", ".join(step.software_tools_used)
            fields.append(FieldText(f"{sp}.software_tools_used", tools))
            fields.append(FieldText(f"{sp}.time_needed", step.time_needed or ""))
            handoff = "" if step.handoff_to is None else str(step.handoff_to)
            fields.append(FieldText(f"{sp}.handoff_to", handoff))
            fields.append(FieldText(f"{sp}._composite", _step_composite(step)))
        for ei, exc in enumerate(proc.exceptions):
            ep = f"{prefix}.exceptions[{ei}]"
            fields.append(FieldText(f"{ep}.what_goes_wrong", exc.what_goes_wrong or ""))
            fields.append(FieldText(f"{ep}.impact", exc.impact or ""))
            fields.append(FieldText(f"{ep}.recovery", exc.recovery or ""))
            fields.append(FieldText(f"{ep}._composite", _exception_composite(exc)))
    return fields


def process_names(profile: GroundTruthProfile | ReconstructedPersona) -> list[tuple[int, str]]:
    return [(i, p.process_name or "") for i, p in enumerate(profile.processes)]


def step_composites(proc: ReconstructedProcess) -> list[tuple[int, str]]:
    return [(i, _step_composite(s)) for i, s in enumerate(proc.steps)]


def exception_composites(proc: ReconstructedProcess) -> list[tuple[int, str]]:
    return [(i, _exception_composite(e)) for i, e in enumerate(proc.exceptions)]
