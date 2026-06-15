"""Orchestrate reconstruction and validation per persona folder."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("harness.evaluation")

from interviewees.evaluation.defaults import DEFAULT_EVALUATION_MODEL, DEFAULT_JUDGE_MODEL
from interviewees.evaluation.embedding_compare import compare_embeddings, embedding_report_to_dict
from interviewees.evaluation.run_folder import RunPaths, resolve_run_paths
from interviewees.evaluation.stage import stage_from_run_folder
from interviewees.evaluation.ground_truth import load_ground_truth_profile
from interviewees.evaluation.interview_artifacts import InterviewSystem, discover_interview_artifacts
from interviewees.evaluation.io import read_json, write_json
from interviewees.evaluation.llm_judge import run_llm_judge
from interviewees.evaluation.reconstruct import reconstruct_interview
from interviewees.evaluation.reconstructed_schema import ReconstructedPersona
from interviewees.evaluation.report_markdown import write_validation_markdown
from interviewees.persona_layout import (
    default_personas_root,
    iter_persona_folders,
    persona_json_in_folder,
    result_json_in_folder,
    validation_json_in_folder,
    validation_summary_path,
)

InterviewSystemName = Literal["noah", "elevenlabs"]
SYSTEMS: tuple[InterviewSystemName, ...] = ("noah", "elevenlabs")


@dataclass
class SummaryRow:
    folder: str
    system: str
    run_id: str = ""
    overall_embedding_similarity: float | None = None
    activity_coverage: int | None = None
    control_flow_and_handoff_fidelity: int | None = None
    attribute_accuracy: int | None = None
    exception_and_edge_case_capture: int | None = None
    faithfulness_no_hallucination: int | None = None
    missed_processes: int = 0
    extra_processes: int = 0
    missed_steps: int = 0
    extra_steps: int = 0
    missed_exceptions: int = 0
    extra_exceptions: int = 0
    status: str = "ok"
    error: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "folder": self.folder,
            "system": self.system,
            "overall_embedding_similarity": self.overall_embedding_similarity,
            "activity_coverage": self.activity_coverage,
            "control_flow_and_handoff_fidelity": self.control_flow_and_handoff_fidelity,
            "attribute_accuracy": self.attribute_accuracy,
            "exception_and_edge_case_capture": self.exception_and_edge_case_capture,
            "faithfulness_no_hallucination": self.faithfulness_no_hallucination,
            "missed_processes": self.missed_processes,
            "extra_processes": self.extra_processes,
            "missed_steps": self.missed_steps,
            "extra_steps": self.extra_steps,
            "missed_exceptions": self.missed_exceptions,
            "extra_exceptions": self.extra_exceptions,
            "status": self.status,
            "error": self.error,
            "timestamp": self.timestamp,
        }
        if self.run_id:
            out["run_id"] = self.run_id
        return out


def _build_validation_report(
    folder_name: str,
    system: str,
    embeddings_dict: dict[str, Any],
    judge_report,
    *,
    run_id: str = "",
    input_dir: str = "",
    output_dir: str = "",
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "folder": folder_name,
        "system": system,
        "reconstruction_file": f"result_{system}.json",
        "ground_truth_file": "persona.json",
        "embeddings": embeddings_dict,
        "judge": {
            "scores": judge_report.scores,
            "justifications": judge_report.justifications,
            "raw_response": judge_report.raw_response,
        },
    }
    if run_id:
        report["run_id"] = run_id
    if input_dir:
        report["input_dir"] = input_dir
    if output_dir:
        report["output_dir"] = output_dir
    return report


def _load_reconstructed(path: Path) -> ReconstructedPersona:
    return ReconstructedPersona.model_validate(read_json(path))


def run_batch_evaluation(
    *,
    personas_root: Path | None = None,
    openai_model: str = DEFAULT_EVALUATION_MODEL,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    force: bool = False,
    skip_reconstruct: bool = False,
    skip_validate: bool = False,
    min_alignment_similarity: float = 0.0,
    run_id: str = "",
    input_dir: str = "",
    output_dir: str = "",
) -> list[SummaryRow]:
    root = personas_root or default_personas_root()
    if not root.is_dir():
        raise FileNotFoundError(f"Personas root not found: {root}")

    logger.info(
        "batch evaluation start root=%s reconstruct_model=%s judge_model=%s force=%s skip_reconstruct=%s skip_validate=%s",
        root,
        openai_model,
        judge_model,
        force,
        skip_reconstruct,
        skip_validate,
    )

    summary_rows: list[SummaryRow] = []

    for folder in iter_persona_folders(root):
        if not persona_json_in_folder(folder).is_file():
            continue

        reports_by_system: dict[str, dict[str, Any]] = {}

        for system in SYSTEMS:
            row = SummaryRow(folder=folder.name, system=system, run_id=run_id)
            label = f"{run_id}/{folder.name}/{system}" if run_id else f"{folder.name}/{system}"
            try:
                logger.info("[%s] start", label)
                artifacts = discover_interview_artifacts(folder, system)  # type: ignore[arg-type]
                result_path = result_json_in_folder(folder, system)

                if artifacts is None and not skip_reconstruct:
                    row.status = "skipped"
                    row.error = "no interview artifacts found"
                    logger.warning("[%s] skipped: %s", label, row.error)
                    summary_rows.append(row)
                    continue

                if not skip_reconstruct:
                    if artifacts is None:
                        raise RuntimeError("no artifacts for reconstruction")
                    sources = ", ".join(artifacts.source_files) or "(none)"
                    logger.info("[%s] reconstructing from %s", label, sources)
                    reconstructed = reconstruct_interview(artifacts, model=openai_model)
                    write_json(result_path, reconstructed, force=force)
                    logger.info("[%s] wrote %s", label, result_path.name)
                elif not result_path.is_file():
                    row.status = "skipped"
                    row.error = f"missing {result_path.name}"
                    logger.warning("[%s] skipped: %s", label, row.error)
                    summary_rows.append(row)
                    continue
                else:
                    reconstructed = _load_reconstructed(result_path)
                    logger.info("[%s] loaded existing %s", label, result_path.name)

                if skip_validate:
                    row.status = "reconstructed_only"
                    logger.info("[%s] reconstructed_only (validation skipped)", label)
                    summary_rows.append(row)
                    continue

                logger.info("[%s] validating against persona.json", label)
                truth = load_ground_truth_profile(folder)
                emb_report = compare_embeddings(
                    truth,
                    reconstructed,
                    min_alignment_similarity=min_alignment_similarity,
                )
                judge_report = run_llm_judge(truth, reconstructed, model=judge_model)
                emb_dict = embedding_report_to_dict(emb_report)
                validation = _build_validation_report(
                    folder.name,
                    system,
                    emb_dict,
                    judge_report,
                    run_id=run_id,
                    input_dir=input_dir,
                    output_dir=output_dir,
                )
                write_json(validation_json_in_folder(folder, system), validation, force=force)
                reports_by_system[system] = validation

                row.overall_embedding_similarity = emb_report.overall_similarity
                row.missed_processes = emb_report.counts.get("missed_processes", 0)
                row.extra_processes = emb_report.counts.get("extra_processes", 0)
                row.missed_steps = emb_report.counts.get("missed_steps", 0)
                row.extra_steps = emb_report.counts.get("extra_steps", 0)
                row.missed_exceptions = emb_report.counts.get("missed_exceptions", 0)
                row.extra_exceptions = emb_report.counts.get("extra_exceptions", 0)
                for dim, score in judge_report.scores.items():
                    setattr(row, dim, score)
                logger.info(
                    "[%s] ok embedding_sim=%.3f judge=%s",
                    label,
                    emb_report.overall_similarity,
                    judge_report.scores,
                )

            except Exception as e:
                row.status = "error"
                row.error = str(e)
                logger.error("[%s] failed: %s", label, e)
                logger.exception("[%s] traceback", label)
            summary_rows.append(row)

        if reports_by_system and not skip_validate:
            write_validation_markdown(
                folder,
                reports_by_system,
                force=force,
                run_id=run_id,
            )

    summary_path = validation_summary_path(root)
    summary_payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": [r.to_dict() for r in summary_rows],
    }
    if run_id:
        summary_payload["run_id"] = run_id
    if input_dir:
        summary_payload["input_dir"] = input_dir
    if output_dir:
        summary_payload["output_dir"] = output_dir
    write_json(summary_path, summary_payload, force=True)
    logger.info("wrote %s", summary_path)
    return summary_rows


def run_evaluation_from_input(
    input_dir: Path,
    *,
    openai_model: str = DEFAULT_EVALUATION_MODEL,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    force: bool = False,
    skip_reconstruct: bool = False,
    skip_validate: bool = False,
    min_alignment_similarity: float = 0.0,
) -> tuple[RunPaths, list[SummaryRow]]:
    """
    Stage artifacts from results/run_N and run reconstruction + validation.

    Output is written to results/validation/{run_id}/.
    """
    paths = resolve_run_paths(input_dir)
    if paths.noah_export is None and paths.elevenlabs_dir is None:
        raise FileNotFoundError(
            f"No interview data found under {paths.input_dir} "
            "(expected noah/output-test-noah_*.json and/or elevenlabs/*.json)"
        )

    logger.info(
        "run %s input=%s output=%s noah_export=%s elevenlabs_dir=%s force=%s",
        paths.run_id,
        paths.input_dir,
        paths.validation_root,
        paths.noah_export,
        paths.elevenlabs_dir,
        force,
    )
    staged = stage_from_run_folder(paths, force=force)
    logger.info("staged %s files into %s", len(staged), paths.validation_root)
    harness = Path(__file__).resolve().parents[2]
    rows = run_batch_evaluation(
        personas_root=paths.validation_root,
        openai_model=openai_model,
        judge_model=judge_model,
        force=force,
        skip_reconstruct=skip_reconstruct,
        skip_validate=skip_validate,
        min_alignment_similarity=min_alignment_similarity,
        run_id=paths.run_id,
        input_dir=_relative_harness(paths.input_dir, harness),
        output_dir=_relative_harness(paths.validation_root, harness),
    )
    return paths, rows


def _relative_harness(path: Path, harness_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(harness_root.resolve()))
    except ValueError:
        return str(path.resolve())
