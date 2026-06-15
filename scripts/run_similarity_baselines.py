"""Floor/ceiling similarity baselines using the evaluation embedding + LLM judge pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_ROOT = REPO_ROOT / "testing-harness"
sys.path.insert(0, str(HARNESS_ROOT))

from interviewees.core.llm_json import MAX_JSON_ATTEMPTS, chat_json  # noqa: E402
from interviewees.env import load_harness_env  # noqa: E402
from interviewees.evaluation.defaults import DEFAULT_JUDGE_MODEL  # noqa: E402
from interviewees.evaluation.embedding_compare import compare_embeddings  # noqa: E402
from interviewees.evaluation.ground_truth import load_ground_truth_profile  # noqa: E402
from interviewees.evaluation.io import read_json, write_json  # noqa: E402
from interviewees.evaluation.llm_judge import JUDGE_DIMENSIONS, run_llm_judge  # noqa: E402
from interviewees.evaluation.reconstructed_schema import (  # noqa: E402
    GroundTruthProfile,
    ReconstructedPersona,
)
from interviewees.persona_layout import default_personas_root, persona_json_in_folder  # noqa: E402

BaselineKind = Literal["floor", "ceiling"]
STANDARD_PERSONAS = ("A", "B", "C", "D")
REFERENCE_FLOOR_FOLDER = "floor-persona"
REFERENCE_CEILING_FOLDER = "ceiling-persona"
COUNTERPART_FILENAME = "counterpart.json"
CEILING_CACHE_FILENAME = "counterpart_ceiling.json"
DEFAULT_OUTPUT = REPO_ROOT / "scripts" / "similarity_baselines_output.txt"


@dataclass
class BaselineResult:
    persona: str
    kind: BaselineKind
    overall_embedding_similarity: float
    judge_scores: dict[str, int] | None
    counts: dict[str, int]
    status: str = "ok"
    error: str = ""


def _load_reconstructed(path: Path) -> ReconstructedPersona:
    return ReconstructedPersona.model_validate(read_json(path))


def _paraphrase_profile(
    truth: GroundTruthProfile,
    *,
    model: str,
    cache_path: Path,
    force: bool,
) -> ReconstructedPersona:
    if cache_path.is_file() and not force:
        return _load_reconstructed(cache_path)

    system = (
        "You lightly paraphrase structured process profiles. "
        "Preserve every process, step, exception, tool, duration, and handoff target. "
        "Change wording only; do not add, remove, or reorder items. "
        "Return strict JSON matching the input schema (name, role, processes)."
    )
    user = (
        "Paraphrase this profile with different wording but identical meaning and structure.\n\n"
        f"{json.dumps(truth.model_dump(mode='json'), indent=2, ensure_ascii=False)}"
    )

    last_error: str | None = None
    for attempt in range(1, MAX_JSON_ATTEMPTS + 1):
        user_msg = user
        if last_error:
            user_msg += f"\n\nValidation error: {last_error}\nReturn valid JSON only."
        try:
            parsed, _ = chat_json(system=system, user=user_msg, model=model, temperature=0.2)
            paraphrased = ReconstructedPersona.model_validate(parsed)
            write_json(cache_path, paraphrased, force=True)
            return paraphrased
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(f"Paraphrase failed after {MAX_JSON_ATTEMPTS} attempts: {last_error}")


def _evaluate_pair(
    truth: GroundTruthProfile,
    reconstructed: ReconstructedPersona,
    *,
    judge_model: str,
    skip_judge: bool,
    min_alignment_similarity: float,
) -> tuple[float, dict[str, int] | None, dict[str, int]]:
    emb_report = compare_embeddings(
        truth,
        reconstructed,
        min_alignment_similarity=min_alignment_similarity,
    )
    judge_scores: dict[str, int] | None = None
    if not skip_judge:
        judge_report = run_llm_judge(truth, reconstructed, model=judge_model)
        judge_scores = judge_report.scores
    return emb_report.overall_similarity, judge_scores, emb_report.counts


def _run_reference_baseline(
    personas_root: Path,
    folder_name: str,
    kind: BaselineKind,
    *,
    judge_model: str,
    skip_judge: bool,
    min_alignment_similarity: float,
) -> BaselineResult:
    folder = personas_root / folder_name
    try:
        truth = load_ground_truth_profile(folder)
        counterpart = _load_reconstructed(folder / COUNTERPART_FILENAME)
        emb, judge, counts = _evaluate_pair(
            truth,
            counterpart,
            judge_model=judge_model,
            skip_judge=skip_judge,
            min_alignment_similarity=min_alignment_similarity,
        )
        return BaselineResult(folder_name, kind, emb, judge, counts)
    except Exception as e:
        return BaselineResult(folder_name, kind, 0.0, None, {}, status="error", error=str(e))


def _run_persona_baselines(
    personas_root: Path,
    persona: str,
    floor_counterpart: ReconstructedPersona,
    *,
    judge_model: str,
    skip_judge: bool,
    min_alignment_similarity: float,
    force_paraphrase: bool,
) -> list[BaselineResult]:
    folder = personas_root / persona
    results: list[BaselineResult] = []

    try:
        truth = load_ground_truth_profile(folder)
    except Exception as e:
        return [
            BaselineResult(persona, "floor", 0.0, None, {}, status="error", error=str(e)),
            BaselineResult(persona, "ceiling", 0.0, None, {}, status="error", error=str(e)),
        ]

    try:
        emb, judge, counts = _evaluate_pair(
            truth,
            floor_counterpart,
            judge_model=judge_model,
            skip_judge=skip_judge,
            min_alignment_similarity=min_alignment_similarity,
        )
        results.append(BaselineResult(persona, "floor", emb, judge, counts))
    except Exception as e:
        results.append(BaselineResult(persona, "floor", 0.0, None, {}, status="error", error=str(e)))

    try:
        ceiling_counterpart = _paraphrase_profile(
            truth,
            model=judge_model,
            cache_path=folder / CEILING_CACHE_FILENAME,
            force=force_paraphrase,
        )
        emb, judge, counts = _evaluate_pair(
            truth,
            ceiling_counterpart,
            judge_model=judge_model,
            skip_judge=skip_judge,
            min_alignment_similarity=min_alignment_similarity,
        )
        results.append(BaselineResult(persona, "ceiling", emb, judge, counts))
    except Exception as e:
        results.append(BaselineResult(persona, "ceiling", 0.0, None, {}, status="error", error=str(e)))

    return results


def _format_judge_scores(scores: dict[str, int] | None) -> str:
    if scores is None:
        return "(judge skipped)"
    parts = [f"{dim}={scores[dim]}" for dim in JUDGE_DIMENSIONS if dim in scores]
    return ", ".join(parts)


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    keys = (
        "missed_processes",
        "extra_processes",
        "missed_steps",
        "extra_steps",
        "missed_exceptions",
        "extra_exceptions",
    )
    return ", ".join(f"{k}={counts.get(k, 0)}" for k in keys)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _render_report(
    reference_results: list[BaselineResult],
    persona_results: list[BaselineResult],
    *,
    personas_root: Path,
    judge_model: str,
    skip_judge: bool,
) -> str:
    lines: list[str] = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append("Similarity baseline evaluation")
    lines.append(f"Generated: {ts}")
    lines.append(f"Personas root: {personas_root}")
    lines.append(f"Judge model: {judge_model} (skip_judge={skip_judge})")
    lines.append("")

    lines.append("=== Reference baselines ===")
    for result in reference_results:
        lines.append(f"[{result.persona} / {result.kind}]")
        if result.status == "error":
            lines.append(f"  ERROR: {result.error}")
            continue
        lines.append(f"  overall_embedding_similarity: {result.overall_embedding_similarity:.3f}")
        lines.append(f"  judge: {_format_judge_scores(result.judge_scores)}")
        counts = _format_counts(result.counts)
        if counts:
            lines.append(f"  alignment_counts: {counts}")
        lines.append("")

    lines.append("=== Per-persona floor & ceiling ===")
    by_persona: dict[str, list[BaselineResult]] = {}
    for result in persona_results:
        by_persona.setdefault(result.persona, []).append(result)

    for persona in STANDARD_PERSONAS:
        lines.append(f"--- Persona {persona} ---")
        for result in by_persona.get(persona, []):
            label = "floor (vs unrelated document)" if result.kind == "floor" else "ceiling (vs paraphrase)"
            lines.append(f"  {label}:")
            if result.status == "error":
                lines.append(f"    ERROR: {result.error}")
                continue
            lines.append(f"    overall_embedding_similarity: {result.overall_embedding_similarity:.3f}")
            lines.append(f"    judge: {_format_judge_scores(result.judge_scores)}")
            counts = _format_counts(result.counts)
            if counts:
                lines.append(f"    alignment_counts: {counts}")
        lines.append("")

    floor_scores = [
        r.overall_embedding_similarity
        for r in (*reference_results, *persona_results)
        if r.kind == "floor" and r.status == "ok"
    ]
    ceiling_scores = [
        r.overall_embedding_similarity
        for r in (*reference_results, *persona_results)
        if r.kind == "ceiling" and r.status == "ok"
    ]
    mean_floor = _mean(floor_scores)
    mean_ceiling = _mean(ceiling_scores)

    lines.append("=== Summary ===")
    lines.append(f"Floor embedding scores (n={len(floor_scores)}): {[round(s, 3) for s in floor_scores]}")
    lines.append(f"Ceiling embedding scores (n={len(ceiling_scores)}): {[round(s, 3) for s in ceiling_scores]}")
    lines.append(f"Mean floor embedding similarity: {mean_floor:.3f}")
    lines.append(f"Mean ceiling embedding similarity: {mean_ceiling:.3f}")
    lines.append("")
    lines.append(
        "To provide context for these scores, a baseline of random document pairs (floor) "
        f"scores approximately {mean_floor:.2f}, while slightly paraphrased identical ground "
        f"truths (ceiling) score around {mean_ceiling:.2f}."
    )
    return "\n".join(lines) + "\n"


def run_baselines(
    *,
    personas_root: Path,
    output_path: Path,
    judge_model: str,
    skip_judge: bool,
    min_alignment_similarity: float,
    force_paraphrase: bool,
    force_output: bool,
) -> str:
    floor_counterpart_path = personas_root / REFERENCE_FLOOR_FOLDER / COUNTERPART_FILENAME
    if not floor_counterpart_path.is_file():
        raise FileNotFoundError(f"Missing floor counterpart: {floor_counterpart_path}")
    floor_counterpart = _load_reconstructed(floor_counterpart_path)

    reference_results = [
        _run_reference_baseline(
            personas_root,
            REFERENCE_FLOOR_FOLDER,
            "floor",
            judge_model=judge_model,
            skip_judge=skip_judge,
            min_alignment_similarity=min_alignment_similarity,
        ),
        _run_reference_baseline(
            personas_root,
            REFERENCE_CEILING_FOLDER,
            "ceiling",
            judge_model=judge_model,
            skip_judge=skip_judge,
            min_alignment_similarity=min_alignment_similarity,
        ),
    ]

    persona_results: list[BaselineResult] = []
    for persona in STANDARD_PERSONAS:
        if not persona_json_in_folder(personas_root / persona).is_file():
            continue
        persona_results.extend(
            _run_persona_baselines(
                personas_root,
                persona,
                floor_counterpart,
                judge_model=judge_model,
                skip_judge=skip_judge,
                min_alignment_similarity=min_alignment_similarity,
                force_paraphrase=force_paraphrase,
            )
        )

    report = _render_report(
        reference_results,
        persona_results,
        personas_root=personas_root,
        judge_model=judge_model,
        skip_judge=skip_judge,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not force_output:
        raise RuntimeError(f"Refusing to overwrite existing file: {output_path}")
    output_path.write_text(report, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run floor (unrelated document) and ceiling (paraphrased ground truth) "
            "similarity baselines using the evaluation embedding + LLM judge pipeline."
        )
    )
    parser.add_argument(
        "--personas-root",
        type=Path,
        default=default_personas_root(),
        help="Personas directory (default: testing-harness/personas)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Text report path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--skip-judge", action="store_true", help="Embedding similarity only")
    parser.add_argument(
        "--min-alignment-similarity",
        type=float,
        default=0.0,
        help="Minimum cosine similarity to accept a greedy alignment pair",
    )
    parser.add_argument(
        "--force-paraphrase",
        action="store_true",
        help="Regenerate cached ceiling paraphrases for A–D",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite output file if it exists")
    args = parser.parse_args()

    load_harness_env()
    report = run_baselines(
        personas_root=args.personas_root.resolve(),
        output_path=args.output.resolve(),
        judge_model=args.judge_model,
        skip_judge=args.skip_judge,
        min_alignment_similarity=args.min_alignment_similarity,
        force_paraphrase=args.force_paraphrase,
        force_output=args.force,
    )
    print(report)
    print(f"Wrote {args.output.resolve()}")


if __name__ == "__main__":
    main()
