"""Paths and discovery for personas/ folder layout (A–D + prompt file per folder)."""

from __future__ import annotations

from pathlib import Path

# Prepared interviewee spec written by tools/prepare_personas.py batch command.
PERSONA_PROMPT_FILENAME = "prompt.yaml"


def default_personas_root() -> Path:
    return Path(__file__).resolve().parents[1] / "personas"


def prompt_file_in_folder(folder: Path) -> Path:
    """YAML persona spec consumed by load_persona() for this folder."""
    return folder / PERSONA_PROMPT_FILENAME


def iter_persona_folders(personas_root: Path) -> list[Path]:
    """Sorted subdirectories of personas/ (e.g. A, B, C, D)."""
    if not personas_root.is_dir():
        return []
    return sorted(p for p in personas_root.iterdir() if p.is_dir())
