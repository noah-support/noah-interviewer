"""Load persona.json for validation only (never used in reconstruction)."""

from __future__ import annotations

from pathlib import Path

from interviewees.core.persona_schema import GeneratedPersona
from interviewees.evaluation.io import read_json
from interviewees.evaluation.reconstructed_schema import GroundTruthProfile, ReconstructedProcess
from interviewees.persona_layout import persona_json_in_folder


def load_ground_truth_profile(folder: Path) -> GroundTruthProfile:
    path = persona_json_in_folder(folder)
    data = read_json(path)
    persona = GeneratedPersona.model_validate(data)
    processes = [
        ReconstructedProcess(
            process_name=p.process_name,
            steps=list(p.steps),
            exceptions=list(p.exceptions),
        )
        for p in persona.processes
    ]
    return GroundTruthProfile(
        name=persona.name,
        role=persona.role,
        processes=processes,
    )
