"""Discover interview run inputs and resolve validation output paths."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from interviewees.evaluation.io import write_json
from interviewees.persona_layout import (
    default_personas_root,
    iter_persona_folders,
    persona_json_in_folder,
)

RUN_MANIFEST_FILENAME = "run_manifest.json"


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    input_dir: Path
    validation_root: Path
    ground_truth_root: Path
    noah_export: Path | None
    elevenlabs_dir: Path | None


def default_results_root(harness_root: Path | None = None) -> Path:
    root = harness_root or Path(__file__).resolve().parents[2]
    return root / "results"


def validation_root_for_run(run_id: str, harness_root: Path | None = None) -> Path:
    return default_results_root(harness_root) / "validation" / run_id


def discover_noah_export(run_dir: Path) -> Path | None:
    noah_dir = run_dir / "noah"
    if not noah_dir.is_dir():
        return None
    candidates = sorted(noah_dir.glob("output-test-noah_*.json"))
    if not candidates:
        candidates = sorted(noah_dir.glob("*.json"))
    return candidates[-1] if candidates else None


def discover_elevenlabs_dir(run_dir: Path) -> Path | None:
    elevenlabs_dir = run_dir / "elevenlabs"
    return elevenlabs_dir if elevenlabs_dir.is_dir() else None


def resolve_run_paths(
    input_dir: Path,
    *,
    harness_root: Path | None = None,
    ground_truth_root: Path | None = None,
) -> RunPaths:
    """Map a results/run_N folder to its validation output tree."""
    resolved_input = input_dir.resolve()
    if not resolved_input.is_dir():
        raise FileNotFoundError(f"Run input directory not found: {resolved_input}")

    run_id = resolved_input.name
    gt_root = (ground_truth_root or default_personas_root()).resolve()
    val_root = validation_root_for_run(run_id, harness_root)

    return RunPaths(
        run_id=run_id,
        input_dir=resolved_input,
        validation_root=val_root,
        ground_truth_root=gt_root,
        noah_export=discover_noah_export(resolved_input),
        elevenlabs_dir=discover_elevenlabs_dir(resolved_input),
    )


def prepare_validation_workspace(paths: RunPaths, *, force: bool = False) -> list[Path]:
    """
    Create results/validation/{run_id}/{A..D}/ with ground-truth persona.json copies.
    """
    written: list[Path] = []
    paths.validation_root.mkdir(parents=True, exist_ok=True)

    for folder in iter_persona_folders(paths.ground_truth_root):
        gt_persona = persona_json_in_folder(folder)
        if not gt_persona.is_file():
            continue
        dest_folder = paths.validation_root / folder.name
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_persona = persona_json_in_folder(dest_folder)
        if dest_persona.exists() and not force:
            written.append(dest_persona)
            continue
        shutil.copy2(gt_persona, dest_persona)
        written.append(dest_persona)

    if not written:
        raise RuntimeError(
            f"No persona.json files found under ground truth root: {paths.ground_truth_root}"
        )
    return written


def build_run_manifest(paths: RunPaths, staged_files: list[Path]) -> dict:
    harness = Path(__file__).resolve().parents[2]
    elevenlabs_sources: dict[str, str] = {}
    if paths.elevenlabs_dir is not None:
        for folder in iter_persona_folders(paths.validation_root):
            src = paths.elevenlabs_dir / f"{folder.name}.json"
            if src.is_file():
                elevenlabs_sources[folder.name] = _relative_to_harness(src, harness)
    return {
        "run_id": paths.run_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_dir": _relative_to_harness(paths.input_dir, harness),
        "output_dir": _relative_to_harness(paths.validation_root, harness),
        "ground_truth_root": _relative_to_harness(paths.ground_truth_root, harness),
        "sources": {
            "noah_export": _relative_to_harness(paths.noah_export, harness)
            if paths.noah_export
            else None,
            "elevenlabs": elevenlabs_sources or None,
        },
        "staged_files": [_relative_to_harness(p, harness) for p in staged_files],
    }


def write_run_manifest(paths: RunPaths, staged_files: list[Path], *, force: bool = False) -> Path:
    manifest_path = paths.validation_root / RUN_MANIFEST_FILENAME
    if manifest_path.exists() and not force:
        return manifest_path
    write_json(manifest_path, build_run_manifest(paths, staged_files), force=True)
    return manifest_path


def _relative_to_harness(path: Path | None, harness_root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(harness_root.resolve()))
    except ValueError:
        return str(path.resolve())
