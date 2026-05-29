"""Run a full project test: sequential interviews per persona, aggregate JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import typer

from interviewees.core.persona import load_persona
from interviewees.elevenlabs_client import run_interview as run_elevenlabs_interview
from interviewees.livekit_client import run_interview as run_livekit_interview
from interviewees.noah_api import NoahApiClient

InterviewerKind = Literal["livekit", "elevenlabs"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _results_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "results"


def discover_personas(personas_dir: Path) -> list[Path]:
    if not personas_dir.is_dir():
        raise typer.BadParameter(f"Personas directory not found: {personas_dir}")
    paths = sorted(personas_dir.glob("*.yaml"))
    if not paths:
        raise typer.BadParameter(f"No persona YAML files in {personas_dir}")
    return paths


def _parse_content_json(content: str) -> Any:
    text = (content or "").strip()
    if not text:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return text


def _write_aggregate(
    *,
    project_name: str,
    interviewer: InterviewerKind,
    mode: str,
    started_at: str,
    interview_results: list[dict[str, Any]],
    project_id: int | None = None,
    project_title: str | None = None,
) -> Path:
    ended_at = _utc_now_iso()
    aggregate: dict[str, Any] = {
        "schema_version": "1.0",
        "project_name": project_name,
        "mode": mode,
        "interviewer": interviewer,
        "started_at": started_at,
        "ended_at": ended_at,
        "interview_count": len(interview_results),
        "interviews": interview_results,
    }
    if project_id is not None:
        aggregate["project_id"] = project_id
    if project_title is not None:
        aggregate["project_title"] = project_title

    out_dir = _results_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{project_name}__{interviewer}__{mode}__{ts}.json"
    out_path.write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


async def run_project_elevenlabs(
    *,
    project_name: str,
    personas_dir: Path,
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
) -> Path:
    """Run all personas sequentially against the hosted ElevenLabs ConvAI agent."""
    persona_paths = discover_personas(personas_dir)
    started_at = _utc_now_iso()
    interview_results: list[dict[str, Any]] = []

    for persona_path in persona_paths:
        persona = load_persona(persona_path)
        typer.echo(f"Starting ElevenLabs interview for {persona.id}...", err=True)

        transcript, transcript_path = await run_elevenlabs_interview(
            persona,
            mode=mode,
            openai_model=openai_model,
            transcript_dir=transcript_dir,
            verbose=verbose,
        )

        interview_results.append(
            {
                "persona_id": persona.id,
                "subject_label": persona.subject_label,
                "persona_path": str(persona_path),
                "harness_transcript_path": transcript_path,
                "harness_transcript": transcript.model_dump(),
                "ended_by": transcript.ended_by,
            }
        )

    return _write_aggregate(
        project_name=project_name,
        interviewer="elevenlabs",
        mode=mode,
        started_at=started_at,
        interview_results=interview_results,
    )


async def run_project_livekit(
    *,
    project_name: str,
    personas_dir: Path,
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
    api_base_url: str | None,
    persist_wait_timeout_s: float,
    project_title: str | None = None,
) -> Path:
    """
    Create a DB project, one interview per persona, run LiveKit sequentially, write aggregate JSON.
    """
    persona_paths = discover_personas(personas_dir)
    started_at = _utc_now_iso()

    title = project_title or f"Harness {project_name} {_utc_now_iso()}"

    admin = NoahApiClient(api_base_url)
    try:
        project = admin.create_project(title)
        project_id = int(project["id"])
    finally:
        admin.close()

    interview_results: list[dict[str, Any]] = []

    for persona_path in persona_paths:
        persona = load_persona(persona_path)
        username = persona.subject_label[:20]

        typer.echo(
            f"Starting LiveKit interview for {persona.id} (DB username={username})...",
            err=True,
        )

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
        entry: dict[str, Any] = {
            "persona_id": persona.id,
            "subject_label": persona.subject_label,
            "persona_path": str(persona_path),
            "interview_id": lk.interview_id,
            "username": lk.username,
            "code": lk.code,
            "room": lk.room,
            "harness_transcript_path": result.transcript_path,
            "harness_transcript": result.transcript.model_dump(),
            "ended_by": result.ended_by,
            "end_api_response": result.end_api_response,
        }
        if db is not None:
            entry["db"] = {
                "status": db.status,
                "content": _parse_content_json(db.content),
                "summary": db.summary,
                "discovery_state": db.discovery_state,
            }
        else:
            entry["db"] = None
            typer.echo(
                f"Warning: no DB record fetched for interview {lk.interview_id}",
                err=True,
            )

        interview_results.append(entry)

    return _write_aggregate(
        project_name=project_name,
        interviewer="livekit",
        mode=mode,
        started_at=started_at,
        interview_results=interview_results,
        project_id=project_id,
        project_title=title,
    )


async def run_project(
    *,
    project_name: str,
    interviewer: InterviewerKind,
    personas_dir: Path,
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
    api_base_url: str | None = None,
    persist_wait_timeout_s: float = 60.0,
    project_title: str | None = None,
) -> Path:
    """Dispatch to LiveKit or ElevenLabs project runner."""
    if interviewer == "elevenlabs":
        return await run_project_elevenlabs(
            project_name=project_name,
            personas_dir=personas_dir,
            mode=mode,
            openai_model=openai_model,
            transcript_dir=transcript_dir,
            verbose=verbose,
        )
    return await run_project_livekit(
        project_name=project_name,
        personas_dir=personas_dir,
        mode=mode,
        openai_model=openai_model,
        transcript_dir=transcript_dir,
        verbose=verbose,
        api_base_url=api_base_url,
        persist_wait_timeout_s=persist_wait_timeout_s,
        project_title=project_title,
    )
