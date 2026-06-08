"""
Discover interview output files per persona folder.

Edit CANONICAL_ARTIFACTS and FALLBACK_GLOBS to adjust naming conventions.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from interviewees.core.transcript import Transcript

InterviewSystem = Literal["noah", "elevenlabs"]

# --- Adjustable conventions (single place) ---

CANONICAL_ARTIFACTS: dict[InterviewSystem, dict[str, tuple[str, ...]]] = {
    "noah": {
        "transcript": ("noah_transcript.json", "noah_transcript.txt"),
        "summary": ("noah_summary.txt", "noah_summary.json"),
        "state": ("noah_state.json",),
    },
    "elevenlabs": {
        "transcript": ("elevenlabs_transcript.json", "elevenlabs_transcript.txt"),
        "summary": ("elevenlabs_summary.txt", "elevenlabs_summary.json"),
        "state": (),
    },
}

FALLBACK_GLOBS: dict[InterviewSystem, dict[str, tuple[str, ...]]] = {
    "noah": {
        "transcript": ("*__livekit__*.json",),
    },
    "elevenlabs": {
        "transcript": ("*__elevenlabs__*.json",),
    },
}

# Never treat these as interview inputs (leakage guard).
DENYLIST_EXACT = frozenset(
    {
        "persona.json",
        "prompt.yaml",
        "validation.md",
    }
)
DENYLIST_GLOBS = ("process*.json", "result_*.json", "validation_*.json")


def is_denied_input(path: Path) -> bool:
    name = path.name
    if name in DENYLIST_EXACT:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in DENYLIST_GLOBS)


@dataclass(frozen=True)
class InterviewArtifacts:
    folder: Path
    system: InterviewSystem
    transcript_path: Path | None
    summary_path: Path | None
    state_path: Path | None
    transcript_text: str = ""
    summary_text: str = ""
    state_json: dict[str, Any] | None = None
    source_files: list[str] = field(default_factory=list)

    def has_content(self) -> bool:
        return bool(
            self.transcript_text.strip()
            or self.summary_text.strip()
            or self.state_json is not None
        )


def _first_existing(folder: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        p = folder / name
        if p.is_file() and not is_denied_input(p):
            return p
    return None


def _glob_fallback(folder: Path, patterns: tuple[str, ...]) -> Path | None:
    candidates: list[Path] = []
    for pat in patterns:
        for p in folder.glob(pat):
            if p.is_file() and not is_denied_input(p):
                candidates.append(p)
    if not candidates:
        return None
    return sorted(candidates, key=lambda x: x.name)[-1]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_content_json(content: str) -> Any:
    text = (content or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _transcript_to_dialogue(data: Any) -> str:
    """Normalize harness Transcript JSON or message lists to dialogue text."""
    if isinstance(data, dict) and "turns" in data:
        try:
            transcript = Transcript.model_validate(data)
            lines: list[str] = []
            for turn in transcript.turns:
                label = "Interviewer" if turn.role == "interviewer" else "Interviewee"
                lines.append(f"{label}: {turn.text}")
            return "\n\n".join(lines)
        except Exception:
            pass

    if isinstance(data, dict) and "content" in data:
        inner = _parse_content_json(str(data.get("content") or ""))
        if inner is not data:
            return _transcript_to_dialogue(inner)

    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                role = str(item.get("role") or item.get("speaker") or "unknown")
                text = str(item.get("text") or item.get("content") or item.get("message") or "")
                if text.strip():
                    lines.append(f"{role}: {text}")
        if lines:
            return "\n\n".join(lines)

    if isinstance(data, str):
        return data

    return json.dumps(data, indent=2, ensure_ascii=False)


def _load_transcript_text(path: Path) -> str:
    raw = _read_text(path)
    if path.suffix.lower() == ".json":
        parsed = _parse_content_json(raw)
        if parsed is not None:
            return _transcript_to_dialogue(parsed)
    return raw


def _load_summary_text(path: Path) -> str:
    raw = _read_text(path)
    if path.suffix.lower() == ".json":
        parsed = _parse_content_json(raw)
        if isinstance(parsed, str):
            return parsed
        if isinstance(parsed, dict) and "summary" in parsed:
            return str(parsed.get("summary") or "")
    return raw


def _load_state_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"State file must be a JSON object: {path.name}")
    return data


def discover_interview_artifacts(
    folder: Path,
    system: InterviewSystem,
) -> InterviewArtifacts | None:
    """
    Resolve interview inputs for one system in a persona folder.

    Returns None if no transcript/summary/state content is available.
    Never reads persona.json or process*.json.
    """
    canon = CANONICAL_ARTIFACTS[system]
    fallbacks = FALLBACK_GLOBS.get(system, {})

    transcript_path = _first_existing(folder, canon.get("transcript", ()))
    if transcript_path is None:
        transcript_path = _glob_fallback(folder, fallbacks.get("transcript", ()))

    summary_path = _first_existing(folder, canon.get("summary", ()))
    state_names = canon.get("state", ())
    state_path = _first_existing(folder, state_names) if state_names else None

    sources: list[str] = []
    transcript_text = ""
    summary_text = ""
    state_json: dict[str, Any] | None = None

    if transcript_path is not None:
        sources.append(transcript_path.name)
        transcript_text = _load_transcript_text(transcript_path)

    if summary_path is not None:
        sources.append(summary_path.name)
        summary_text = _load_summary_text(summary_path)

    if state_path is not None:
        sources.append(state_path.name)
        state_json = _load_state_json(state_path)

    artifacts = InterviewArtifacts(
        folder=folder,
        system=system,
        transcript_path=transcript_path,
        summary_path=summary_path,
        state_path=state_path,
        transcript_text=transcript_text,
        summary_text=summary_text,
        state_json=state_json,
        source_files=sources,
    )
    if not artifacts.has_content():
        return None
    return artifacts


def format_artifacts_for_prompt(artifacts: InterviewArtifacts) -> str:
    """Serialize discovered artifacts for the reconstruction LLM."""
    parts: list[str] = [
        f"Interview system: {artifacts.system}",
        f"Source files: {', '.join(artifacts.source_files) or '(none)'}",
        "",
    ]
    if artifacts.transcript_text.strip():
        parts.extend(["## Transcript", artifacts.transcript_text.strip(), ""])
    if artifacts.summary_text.strip():
        parts.extend(["## Summary", artifacts.summary_text.strip(), ""])
    if artifacts.state_json is not None:
        parts.extend(
            [
                "## State (JSON)",
                json.dumps(artifacts.state_json, indent=2, ensure_ascii=False),
                "",
            ]
        )
    return "\n".join(parts).strip()
