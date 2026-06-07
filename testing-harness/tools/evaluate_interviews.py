from __future__ import annotations

from pathlib import Path

import typer

from interviewees.env import load_harness_env
from interviewees.evaluation.pipeline import run_batch_evaluation
from interviewees.evaluation.stage import stage_artifacts
from interviewees.persona_layout import default_personas_root

app = typer.Typer(add_completion=False)


@app.callback()
def _load_dotenv() -> None:
    load_harness_env()


@app.command("batch")
def batch(
    personas_root: Path = typer.Option(
        default_personas_root(),
        "--personas-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
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
        force=force,
        skip_reconstruct=skip_reconstruct,
        skip_validate=skip_validate,
        min_alignment_similarity=min_alignment_similarity,
    )
    ok = sum(1 for r in rows if r.status == "ok")
    typer.echo(f"Done: {ok}/{len(rows)} system runs completed successfully.")


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
