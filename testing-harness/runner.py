from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from dotenv import load_dotenv

from interviewees.core.persona import load_persona

app = typer.Typer(add_completion=False)


def _load_env() -> None:
    load_dotenv(Path(__file__).parent / ".env", override=False)


@app.command("interview")
def run_single_interview(
    persona: Path = typer.Option(..., "--persona", exists=True, readable=True),
    interviewer: str = typer.Option(..., "--interviewer"),
    mode: str = typer.Option("full", "--mode"),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
    transcript_dir: Path | None = typer.Option(None, "--transcript-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Run one interview end-to-end and write a transcript JSON."""
    _load_env()

    if interviewer not in ("elevenlabs", "livekit"):
        raise typer.BadParameter("--interviewer must be one of: elevenlabs, livekit")
    if mode not in ("smoke", "full"):
        raise typer.BadParameter("--mode must be one of: smoke, full")

    if mode == "smoke":
        typer.echo("Smoke mode active (turn cap 10).", err=True)

    p = load_persona(persona)

    try:
        if interviewer == "elevenlabs":
            from interviewees.elevenlabs_client import run_interview as run_el

            _, out_path = asyncio.run(
                run_el(
                    p,
                    mode=mode,
                    openai_model=openai_model,
                    transcript_dir=str(transcript_dir) if transcript_dir else None,
                    verbose=verbose,
                )
            )
        else:
            from interviewees.livekit_client import run_interview as run_lk

            result = asyncio.run(
                run_lk(
                    p,
                    mode=mode,
                    openai_model=openai_model,
                    transcript_dir=str(transcript_dir) if transcript_dir else None,
                    verbose=verbose,
                )
            )
            out_path = result.transcript_path
            if result.db_record:
                typer.echo(
                    f"DB persisted: interview_id={result.interview_id} "
                    f"status={result.db_record.status}",
                    err=True,
                )

        typer.echo(out_path)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command("project")
def run_project(
    project: str = typer.Option(..., "--project", help="Project name, e.g. ComputerRepair_1"),
    interviewer: str = typer.Option(
        "livekit",
        "--interviewer",
        help="Interviewer transport: livekit (Noah stack) or elevenlabs (hosted ConvAI)",
    ),
    personas_dir: Path | None = typer.Option(
        None,
        "--personas-dir",
        help="Directory with persona YAMLs (default: personas/<project>/)",
    ),
    mode: str = typer.Option("full", "--mode"),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
    transcript_dir: Path | None = typer.Option(None, "--transcript-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        help="Noah API base URL (LiveKit only)",
    ),
    persist_wait_timeout: float = typer.Option(
        60.0,
        "--persist-wait-timeout",
        help="Seconds to wait for Celery summary/content after /end (LiveKit only)",
    ),
    project_title: str | None = typer.Option(
        None,
        "--project-title",
        help="Optional DB project title (LiveKit only; default: Harness <project> <timestamp>)",
    ),
) -> None:
    """
    Run all personas for a project sequentially; writes one aggregate JSON under results/.

    LiveKit: DB project + interviews, auto token/room, /end, transcript/summary/state in DB.
    ElevenLabs: one ConvAI session per persona; harness transcripts in aggregate JSON only.
    """
    _load_env()

    if interviewer not in ("elevenlabs", "livekit"):
        raise typer.BadParameter("--interviewer must be one of: elevenlabs, livekit")
    if mode not in ("smoke", "full"):
        raise typer.BadParameter("--mode must be one of: smoke, full")

    if mode == "smoke":
        typer.echo("Smoke mode active (turn cap 10 per interviewee).", err=True)

    pdir = personas_dir or (Path(__file__).parent / "personas" / project)

    from interviewees.project_runner import run_project

    try:
        out_path = asyncio.run(
            run_project(
                project_name=project,
                interviewer=interviewer,  # type: ignore[arg-type]
                personas_dir=pdir,
                mode=mode,
                openai_model=openai_model,
                transcript_dir=str(transcript_dir) if transcript_dir else None,
                verbose=verbose,
                api_base_url=api_url,
                persist_wait_timeout_s=persist_wait_timeout,
                project_title=project_title,
            )
        )
        typer.echo(str(out_path))
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    persona: Path | None = typer.Option(None, "--persona", exists=True, readable=True),
    interviewer: str | None = typer.Option(None, "--interviewer"),
    mode: str = typer.Option("full", "--mode"),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
    transcript_dir: Path | None = typer.Option(None, "--transcript-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Backward-compatible entry: `runner.py --persona ... --interviewer ...` runs one interview."""
    if ctx.invoked_subcommand is not None:
        return
    if persona is None or interviewer is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)
    run_single_interview(
        persona=persona,
        interviewer=interviewer,
        mode=mode,
        openai_model=openai_model,
        transcript_dir=transcript_dir,
        verbose=verbose,
    )


if __name__ == "__main__":
    app()
