"""Transcript recording and JSON export."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

EndedBy = Literal[
    "sentinel", "closing", "turn_cap", "error", "manual", "idle_timeout"
]
TurnRole = Literal["interviewer", "interviewee"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Turn(BaseModel):
    index: int
    role: TurnRole
    text: str
    timestamp: str


class Transcript(BaseModel):
    schema_version: str = "1.0"
    persona_id: str
    project: str
    subject_label: str
    interviewer: str
    started_at: str
    ended_at: str = ""
    ended_by: EndedBy = "manual"
    turn_count: int = 0
    turns: list[Turn] = Field(default_factory=list)


class TranscriptRecorder:
    """Accumulate turns and metadata for a single interview session."""

    def __init__(
        self,
        *,
        persona_id: str,
        project: str,
        subject_label: str,
        interviewer: str,
    ) -> None:
        self._persona_id = persona_id
        self._project = project
        self._subject_label = subject_label
        self._interviewer = interviewer
        self._started_at = _utc_now_iso()
        self._ended_at = ""
        self._ended_by: EndedBy = "manual"
        self._turns: list[Turn] = []
        self._next_index = 0

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    def add_interviewer(self, text: str) -> Turn:
        return self._add("interviewer", text)

    def add_interviewee(self, text: str) -> Turn:
        return self._add("interviewee", text)

    def _add(self, role: TurnRole, text: str) -> Turn:
        turn = Turn(
            index=self._next_index,
            role=role,
            text=text,
            timestamp=_utc_now_iso(),
        )
        self._turns.append(turn)
        self._next_index += 1
        return turn

    def finish(self, ended_by: EndedBy) -> Transcript:
        self._ended_at = _utc_now_iso()
        self._ended_by = ended_by
        return self.to_transcript()

    def to_transcript(self) -> Transcript:
        return Transcript(
            persona_id=self._persona_id,
            project=self._project,
            subject_label=self._subject_label,
            interviewer=self._interviewer,
            started_at=self._started_at,
            ended_at=self._ended_at or _utc_now_iso(),
            ended_by=self._ended_by,
            turn_count=len(self._turns),
            turns=list(self._turns),
        )


def transcript_filename(
    subject_label: str,
    interviewer: str,
    *,
    timestamp: str | None = None,
) -> str:
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{subject_label}__{interviewer}__{ts}.json"


def default_transcript_dir(
    project: str,
    *,
    smoke: bool = False,
    override: str | Path | None = None,
) -> Path:
    if override is not None:
        return Path(override)
    base = Path(__file__).resolve().parents[2] / "transcripts"
    if smoke:
        return base / "_smoke"
    return base / project


def write_transcript(path: Path, transcript: Transcript) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(transcript.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
