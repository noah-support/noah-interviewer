from __future__ import annotations

from pathlib import Path

import typer

from interviewees.core.logging_config import configure_harness_logging
from interviewees.env import load_harness_env
from interviewees.evaluation.defaults import DEFAULT_EVALUATION_MODEL, DEFAULT_JUDGE_MODEL
from interviewees.evaluation.pipeline import run_batch_evaluation, run_evaluation_from_input
from interviewees.evaluation.report import format_run_report
from interviewees.evaluation.stage import stage_artifacts
from interviewees.persona_layout import default_personas_root

app = typer.Typer(add_completion=False)


@app.callback()
def _load_dotenv(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging to stderr"),
) -> None:
    load_harness_env()
    configure_harness_logging(verbose=verbose)


def _echo_run_summary(rows: list, *, paths=None) -> int:
    """Print summary; return exit code (1 if any errors)."""
    if paths is not None:
        typer.echo(f"Run: {paths.run_id}")
        typer.echo(f"Input:  {paths.input_dir}")
        typer.echo(f"Output: {paths.validation_root}")
    typer.echo(format_run_report(rows))
    return 1 if any(r.status == "error" for r in rows) else 0


@app.command("run")
def run(
    input_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Run folder, e.g. results/run_1 (contains noah/ and elevenlabs/)",
    ),
    openai_model: str = typer.Option(
        DEFAULT_EVALUATION_MODEL,
        "--openai-model",
        help=f"OpenAI model for reconstruction (default: {DEFAULT_EVALUATION_MODEL})",
    ),
    judge_model: str = typer.Option(
        DEFAULT_JUDGE_MODEL,
        "--judge-model",
        help=f"OpenAI model for LLM judge (default: {DEFAULT_JUDGE_MODEL})",
    ),
    force: bool = typer.Option(False, "--force"),
    skip_reconstruct: bool = typer.Option(False, "--skip-reconstruct"),
    skip_validate: bool = typer.Option(False, "--skip-validate"),
    min_alignment_similarity: float = typer.Option(
        0.0,
        "--min-alignment-similarity",
        help="Minimum cosine similarity to accept a greedy alignment pair",
    ),
) -> None:
    """
    Post-processor: stage interview outputs from a run folder and evaluate them.

    Input:  results/run_1/  (or run_2, …)
    Output: results/validation/run_1/  (mirrors the run name)
    """
    paths, rows = run_evaluation_from_input(
        input_dir.resolve(),
        openai_model=openai_model,
        judge_model=judge_model,
        force=force,
        skip_reconstruct=skip_reconstruct,
        skip_validate=skip_validate,
        min_alignment_similarity=min_alignment_similarity,
    )
    raise typer.Exit(_echo_run_summary(rows, paths=paths))


@app.command("batch")
def batch(
    personas_root: Path = typer.Option(
        default_personas_root(),
        "--personas-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    openai_model: str = typer.Option(DEFAULT_EVALUATION_MODEL, "--openai-model"),
    judge_model: str = typer.Option(DEFAULT_JUDGE_MODEL, "--judge-model"),
    force: bool = typer.Option(False, "--force"),
    skip_reconstruct: bool = typer.Option(False, "--skip-reconstruct"),
    skip_validate: bool = typer.Option(False, "--skip-validate"),
    min_alignment_similarity: float = typer.Option(
        0.0,
        "--min-alignment-similarity",
        help="Minimum cosine similarity to accept a greedy alignment pair",
    ),
) -> None:
    """
    Reconstruct process profiles from interview artifacts and validate against persona.json.

    Processes folders A→D; for each folder runs Noah then ElevenLabs.
    Writes result_{system}.json, validation_{system}.json, and validation.md per folder.
    """
    rows = run_batch_evaluation(
        personas_root=personas_root.resolve(),
        openai_model=openai_model,
        judge_model=judge_model,
        force=force,
        skip_reconstruct=skip_reconstruct,
        skip_validate=skip_validate,
        min_alignment_similarity=min_alignment_similarity,
    )
    raise typer.Exit(_echo_run_summary(rows))


@app.command("stage")
def stage(
    personas_root: Path = typer.Option(
        default_personas_root(),
        "--personas-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    noah_export: Path | None = typer.Option(
        None,
        "--noah-export",
        exists=True,
        readable=True,
        help="Batch Noah JSON (output-test-noah_*.json) → noah_* files per folder",
    ),
    transcripts_root: Path | None = typer.Option(
        None,
        "--transcripts-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Search for {folder}__elevenlabs__*.json under this tree",
    ),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Copy harness outputs into canonical artifact names under each persona folder."""
    if noah_export is None and transcripts_root is None:
        raise typer.BadParameter("Provide --noah-export and/or --transcripts-root")

    paths = stage_artifacts(
        personas_root=personas_root.resolve(),
        noah_export=noah_export,
        transcripts_root=transcripts_root,
        force=force,
    )
    for p in paths:
        typer.echo(f"Wrote {p}")


if __name__ == "__main__":
    app()
