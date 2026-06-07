"""Copy harness outputs into canonical persona-folder artifact names."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from interviewees.persona_layout import default_personas_root, iter_persona_folders


def _parse_content_json(content: str) -> Any:
    text = (content or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def stage_noah_export(
    export_path: Path,
    personas_root: Path,
    *,
    force: bool = False,
) -> list[Path]:
    """Write noah_transcript.json, noah_summary.txt, noah_state.json per folder from batch export."""
    data = json.loads(export_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Noah export must be a JSON object keyed by folder name")

    written: list[Path] = []
    for folder_name, entry in data.items():
        if folder_name not in {f.name for f in iter_persona_folders(personas_root)}:
            continue
        if not isinstance(entry, dict):
            continue
        folder = personas_root / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        content = entry.get("content")
        if content is not None:
            p = folder / "noah_transcript.json"
            if p.exists() and not force:
                raise RuntimeError(f"Refusing to overwrite {p}")
            payload = content if isinstance(content, (dict, list)) else _parse_content_json(str(content))
            p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written.append(p)

        summary = entry.get("summary")
        if summary is not None and str(summary).strip():
            p = folder / "noah_summary.txt"
            if p.exists() and not force:
                raise RuntimeError(f"Refusing to overwrite {p}")
            p.write_text(str(summary).strip() + "\n", encoding="utf-8")
            written.append(p)

        state = entry.get("discovery_state_json")
        if state is not None:
            p = folder / "noah_state.json"
            if p.exists() and not force:
                raise RuntimeError(f"Refusing to overwrite {p}")
            if isinstance(state, str):
                state = _parse_content_json(state)
            p.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written.append(p)

    return written


def stage_elevenlabs_transcripts(
    transcripts_root: Path,
    personas_root: Path,
    *,
    force: bool = False,
) -> list[Path]:
    """Copy latest {folder}__elevenlabs__*.json into personas/{folder}/elevenlabs_transcript.json."""
    written: list[Path] = []
    for folder in iter_persona_folders(personas_root):
        pattern = f"{folder.name}__elevenlabs__*.json"
        candidates = sorted(transcripts_root.rglob(pattern))
        if not candidates:
            candidates = sorted(transcripts_root.glob(pattern))
        if not candidates:
            continue
        src = candidates[-1]
        dest = folder / "elevenlabs_transcript.json"
        if dest.exists() and not force:
            raise RuntimeError(f"Refusing to overwrite {dest}")
        shutil.copy2(src, dest)
        written.append(dest)
    return written


def stage_artifacts(
    *,
    personas_root: Path | None = None,
    noah_export: Path | None = None,
    transcripts_root: Path | None = None,
    force: bool = False,
) -> list[Path]:
    root = personas_root or default_personas_root()
    paths: list[Path] = []
    if noah_export is not None:
        paths.extend(stage_noah_export(noah_export, root, force=force))
    if transcripts_root is not None:
        paths.extend(stage_elevenlabs_transcripts(transcripts_root, root, force=force))
    return paths
