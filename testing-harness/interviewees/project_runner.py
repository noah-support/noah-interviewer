"""Batch output-test runner: sequential interviews per persona folder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import typer
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

from interviewees.core.persona import load_persona
from interviewees.elevenlabs_client import run_interview as run_elevenlabs_interview
from interviewees.livekit_client import run_interview as run_livekit_interview
from interviewees.noah_api import InterviewRecord, NoahApiClient
from interviewees.persona_layout import (
    PERSONA_JSON_FILENAME,
    default_personas_root,
    iter_persona_folders,
    persona_json_in_folder,
)

OUTPUT_TEST_PROJECT_NOAH = "output-test-noah"
InterviewerKind = Literal["noah", "elevenlabs"]


@dataclass(frozen=True)
class PersonaSpec:
    folder_name: str
    json_path: Path


@dataclass(frozen=True)
class BatchRunResult:
    interview_count: int
    interviewer: InterviewerKind
    json_export_path: Path | None


def discover_persona_folders(personas_root: Path | None = None) -> list[PersonaSpec]:
    """Discover persona folders; each must contain persona.json from persona prep batch."""
    root = personas_root or default_personas_root()
    if not root.is_dir():
        raise typer.BadParameter(f"Personas root not found: {root}")

    specs: list[PersonaSpec] = []
    for folder in iter_persona_folders(root):
        json_path = persona_json_in_folder(folder)
        if not json_path.is_file():
            raise typer.BadParameter(
                f"Missing {PERSONA_JSON_FILENAME} in {folder.name}/ "
                f"(run: python tools/prepare_personas.py batch)"
            )
        specs.append(PersonaSpec(folder_name=folder.name, json_path=json_path))

    if not specs:
        raise typer.BadParameter(f"No persona folders under {root}")
    return specs


def _parse_content_json(content: str) -> Any:
    text = (content or "").strip()
    if not text:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return text


def _parse_discovery_state_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": text}


def _export_entry_from_record(db: InterviewRecord) -> dict[str, Any]:
    raw_state = str(db.raw.get("discovery_state_json") or "")
    return {
        "content": _parse_content_json(db.content),
        "discovery_state_json": _parse_discovery_state_json(raw_state),
        "summary": db.summary or "",
    }


def _write_noah_output_json(
    *,
    output_dir: Path,
    entries: dict[str, dict[str, Any]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = output_dir / f"output-test-noah_{ts}.json"
    out_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


async def run_output_test_batch(
    *,
    interviewer: InterviewerKind,
    output_dir: Path,
    personas_root: Path | None = None,
    mode: str = "full",
    openai_model: str = "gpt-4o",
    transcript_dir: str | None = None,
    verbose: bool = False,
    api_base_url: str | None = None,
    persist_wait_timeout_s: float = 60.0,
) -> BatchRunResult:
    """Run all persona folders sequentially (Noah with DB + JSON export; ElevenLabs only)."""
    specs = discover_persona_folders(personas_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    if interviewer == "elevenlabs":
        return await _run_batch_elevenlabs(
            specs=specs,
            mode=mode,
            openai_model=openai_model,
            transcript_dir=transcript_dir,
            verbose=verbose,
        )

    return await _run_batch_noah(
        specs=specs,
        output_dir=output_dir,
        mode=mode,
        openai_model=openai_model,
        transcript_dir=transcript_dir,
        verbose=verbose,
        api_base_url=api_base_url,
        persist_wait_timeout_s=persist_wait_timeout_s,
    )


async def _run_batch_elevenlabs(
    *,
    specs: list[PersonaSpec],
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
) -> BatchRunResult:
    total = len(specs)
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("({task.completed}/{task.total})"),
    ) as progress:
        task_id = progress.add_task("Interviews", total=total)
        for spec in specs:
            progress.update(task_id, description=f"Running {spec.folder_name}")
            persona = load_persona(spec.json_path)
            await run_elevenlabs_interview(
                persona,
                mode=mode,
                openai_model=openai_model,
                transcript_dir=transcript_dir,
                verbose=verbose,
            )
            progress.advance(task_id)

    return BatchRunResult(
        interview_count=total,
        interviewer="elevenlabs",
        json_export_path=None,
    )


async def _run_batch_noah(
    *,
    specs: list[PersonaSpec],
    output_dir: Path,
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
    api_base_url: str | None,
    persist_wait_timeout_s: float,
) -> BatchRunResult:
    admin = NoahApiClient(api_base_url)
    try:
        project_id = admin.find_or_create_project_by_title(OUTPUT_TEST_PROJECT_NOAH)
    finally:
        admin.close()

    export_entries: dict[str, dict[str, Any]] = {}
    total = len(specs)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("({task.completed}/{task.total})"),
    ) as progress:
        task_id = progress.add_task("Interviews", total=total)
        for spec in specs:
            progress.update(task_id, description=f"Running {spec.folder_name}")
            persona = load_persona(spec.json_path)
            username = persona.subject_label[:20]

            with NoahApiClient(api_base_url) as api:
                lk = api.provision_livekit_session(project_id, username=username)
                result = await run_livekit_interview(
                    persona,
                    mode=mode,
                    openai_model=openai_model,
                    transcript_dir=transcript_dir,
                    verbose=verbose,
                    livekit_session=lk,
                    noah_api=api,
                    persist_wait_timeout_s=persist_wait_timeout_s,
                )

            db = result.db_record
            if db is None:
                typer.echo(
                    f"Warning: no DB record for {spec.folder_name} "
                    f"(interview_id={lk.interview_id})",
                    err=True,
                )
                export_entries[spec.folder_name] = {
                    "content": None,
                    "discovery_state_json": None,
                    "summary": "",
                }
            else:
                export_entries[spec.folder_name] = _export_entry_from_record(db)

            progress.advance(task_id)

    json_path = _write_noah_output_json(output_dir=output_dir, entries=export_entries)
    return BatchRunResult(
        interview_count=total,
        interviewer="noah",
        json_export_path=json_path,
    )
