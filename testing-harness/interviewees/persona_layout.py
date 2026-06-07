"""Paths and discovery for personas/ folder layout (A–D + prompt file per folder)."""

from __future__ import annotations

from pathlib import Path

# Prepared interviewee spec (legacy YAML; harness interview runs).
PERSONA_PROMPT_FILENAME = "prompt.yaml"

# Ground-truth persona for process-mining evaluation (tools/prepare_personas.py batch).
PERSONA_JSON_FILENAME = "persona.json"

# Evaluation outputs (tools/evaluate_interviews.py).
VALIDATION_MD_FILENAME = "validation.md"
VALIDATION_SUMMARY_FILENAME = "validation_summary.json"


def result_json_in_folder(folder: Path, system: str) -> Path:
    return folder / f"result_{system}.json"


def validation_json_in_folder(folder: Path, system: str) -> Path:
    return folder / f"validation_{system}.json"


def validation_md_in_folder(folder: Path) -> Path:
    return folder / VALIDATION_MD_FILENAME


def validation_summary_path(personas_root: Path) -> Path:
    return personas_root / VALIDATION_SUMMARY_FILENAME


def default_personas_root() -> Path:
    return Path(__file__).resolve().parents[1] / "personas"


def prompt_file_in_folder(folder: Path) -> Path:
    """Legacy YAML interview spec (optional; harness uses persona.json)."""
    return folder / PERSONA_PROMPT_FILENAME


def persona_json_in_folder(folder: Path) -> Path:
    """Structured ground-truth persona written by prepare_personas batch."""
    return folder / PERSONA_JSON_FILENAME


def iter_persona_folders(personas_root: Path) -> list[Path]:
    """Sorted subdirectories of personas/ (e.g. A, B, C, D)."""
    if not personas_root.is_dir():
        return []
    return sorted(p for p in personas_root.iterdir() if p.is_dir())
