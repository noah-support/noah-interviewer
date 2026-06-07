from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer

from interviewees.core.logging_config import configure_harness_logging
from interviewees.core.persona import Persona, load_persona
from interviewees.env import load_harness_env

import logging

log = logging.getLogger("harness.runner")

app = typer.Typer(add_completion=False)

VALID_INTERVIEWERS = ("noah", "elevenlabs")


def _load_env() -> None:
    load_harness_env()


def _normalize_interviewer(interviewer: str) -> str:
    """Map CLI names to transport client names."""
    if interviewer == "noah":
        return "livekit"
    if interviewer in ("elevenlabs", "livekit"):
        return interviewer
    raise typer.BadParameter(
        f"--interviewer must be one of: {', '.join(VALID_INTERVIEWERS)}"
    )


def _validate_batch_interviewer(interviewer: str) -> str:
    if interviewer not in VALID_INTERVIEWERS:
        raise typer.BadParameter(
            f"--interviewer must be one of: {', '.join(VALID_INTERVIEWERS)}"
        )
    return interviewer


def _livekit_room_configured() -> bool:
    return bool((os.environ.get("LIVEKIT_ROOM") or "").strip())


async def _run_single_noah_interview(
    persona: Persona,
    *,
    mode: str,
    openai_model: str,
    transcript_dir: str | None,
    verbose: bool,
    api_base_url: str | None,
    persist_wait_timeout_s: float,
):
    from interviewees.livekit_client import run_interview as run_lk
    from interviewees.noah_api import NoahApiClient
    from interviewees.project_runner import OUTPUT_TEST_PROJECT_NOAH

    if _livekit_room_configured():
        return await run_lk(
            persona,
            mode=mode,
            openai_model=openai_model,
            transcript_dir=transcript_dir,
            verbose=verbose,
            persist_wait_timeout_s=persist_wait_timeout_s,
        )

    admin = NoahApiClient(api_base_url)
    try:
        project_id = admin.find_or_create_project_by_title(OUTPUT_TEST_PROJECT_NOAH)
    finally:
        admin.close()

    username = persona.subject_label[:20]
    typer.echo(
        f"Provisioning LiveKit via Noah API (project_id={project_id}, username={username})...",
        err=True,
    )

    with NoahApiClient(api_base_url) as api:
        lk = api.provision_livekit_session(project_id, username=username)
        return await run_lk(
            persona,
            mode=mode,
            openai_model=openai_model,
            transcript_dir=transcript_dir,
            verbose=verbose,
            livekit_session=lk,
            noah_api=api,
            persist_wait_timeout_s=persist_wait_timeout_s,
        )


@app.command("interview")
def run_single_interview(
    persona: Path = typer.Option(..., "--persona", exists=True, readable=True),
    interviewer: str = typer.Option(..., "--interviewer"),
    mode: str = typer.Option("full", "--mode"),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
    transcript_dir: Path | None = typer.Option(None, "--transcript-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        help="Noah API base URL (noah only; used to provision token/room when LIVEKIT_ROOM unset)",
    ),
    persist_wait_timeout: float = typer.Option(
        60.0,
        "--persist-wait-timeout",
        help="Seconds to wait for DB content/summary after /end (noah, API provision path)",
    ),
) -> None:
    """Run one interview end-to-end and write a transcript JSON (local debugging)."""
    _load_env()
    configure_harness_logging(verbose=verbose)

    transport = _normalize_interviewer(interviewer)
    if mode not in ("smoke", "full"):
        raise typer.BadParameter("--mode must be one of: smoke, full")

    if mode == "smoke":
        typer.echo("Smoke mode active (10-turn cap, transcripts under transcripts/_smoke/).", err=True)

    p = load_persona(persona)
    log.info(
        "starting interview persona=%s interviewer=%s mode=%s",
        persona,
        interviewer,
        mode,
    )

    try:
        if transport == "elevenlabs":
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
            result = asyncio.run(
                _run_single_noah_interview(
                    p,
                    mode=mode,
                    openai_model=openai_model,
                    transcript_dir=str(transcript_dir) if transcript_dir else None,
                    verbose=verbose,
                    api_base_url=api_url,
                    persist_wait_timeout_s=persist_wait_timeout,
                )
            )
            out_path = result.transcript_path
            if result.db_record:
                typer.echo(
                    f"DB persisted: interview_id={result.interview_id} "
                    f"status={result.db_record.status}",
                    err=True,
                )

        log.info("interview finished transcript=%s", out_path)
        typer.echo(out_path)
    except Exception as e:
        log.exception("interview failed: %s", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


def _run_output_test(
    *,
    interviewer: str,
    output_dir: Path,
    mode: str,
    openai_model: str,
    transcript_dir: Path | None,
    verbose: bool,
    api_url: str | None,
    persist_wait_timeout: float,
    personas_root: Path | None,
) -> None:
    from interviewees.project_runner import run_output_test_batch

    batch_interviewer = _validate_batch_interviewer(interviewer)  # type: ignore[assignment]

    if mode not in ("smoke", "full"):
        raise typer.BadParameter("--mode must be one of: smoke, full")
    if mode == "smoke":
        typer.echo("Smoke mode active (10-turn cap, transcripts under transcripts/_smoke/).", err=True)

    try:
        result = asyncio.run(
            run_output_test_batch(
                interviewer=batch_interviewer,  # type: ignore[arg-type]
                output_dir=output_dir,
                personas_root=personas_root,
                mode=mode,
                openai_model=openai_model,
                transcript_dir=str(transcript_dir) if transcript_dir else None,
                verbose=verbose,
                api_base_url=api_url,
                persist_wait_timeout_s=persist_wait_timeout,
            )
        )
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    if result.interviewer == "noah" and result.json_export_path is not None:
        typer.echo(
            f"Ran {result.interview_count} interviews (noah). "
            f"Wrote {result.json_export_path}",
            err=True,
        )
    else:
        typer.echo(
            f"Ran {result.interview_count} interviews (elevenlabs). "
            "No DB or JSON export.",
            err=True,
        )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    interviewer: str | None = typer.Option(
        None,
        "--interviewer",
        help="Interviewer: noah (local LiveKit) or elevenlabs (hosted ConvAI)",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        help="Directory for Noah combined JSON export",
    ),
    mode: str = typer.Option("full", "--mode"),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
    transcript_dir: Path | None = typer.Option(None, "--transcript-dir"),
    verbose: bool = typer.Option(False, "--verbose"),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        help="Noah API base URL (noah interviewer only)",
    ),
    persist_wait_timeout: float = typer.Option(
        60.0,
        "--persist-wait-timeout",
        help="Seconds to wait for Celery summary/content after /end (noah only)",
    ),
    personas_root: Path | None = typer.Option(
        None,
        "--personas-root",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Root containing persona folders (default: personas/)",
    ),
    persona: Path | None = typer.Option(
        None,
        "--persona",
        exists=True,
        readable=True,
        help="Single persona JSON (debug); use with interview subcommand instead",
    ),
) -> None:
    """
    Batch output test: run all personas under personas/<folder>/ sequentially.

    Example: python3 runner.py --interviewer noah --output-dir ./out
    """
    if ctx.invoked_subcommand is not None:
        return

    _load_env()
    configure_harness_logging(verbose=verbose)

    if persona is not None:
        raise typer.BadParameter(
            "Use `runner.py interview --persona ... --interviewer ...` for a single run."
        )

    if interviewer is None or output_dir is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)

    _run_output_test(
        interviewer=interviewer,
        output_dir=output_dir,
        mode=mode,
        openai_model=openai_model,
        transcript_dir=transcript_dir,
        verbose=verbose,
        api_url=api_url,
        persist_wait_timeout=persist_wait_timeout,
        personas_root=personas_root,
    )


if __name__ == "__main__":
    app()
