"""Embedding-based field comparison (2a)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from interviewees.core.embeddings import embed_texts
from interviewees.evaluation.align import AlignmentPair, AlignmentResult, cosine_similarity, greedy_align
from interviewees.evaluation.flatten import exception_composites, process_names, step_composites
from interviewees.evaluation.reconstructed_schema import GroundTruthProfile, ReconstructedPersona


@dataclass
class FieldSimilarity:
    path: str
    truth_text: str
    recon_text: str
    similarity: float


@dataclass
class ProcessEmbeddingReport:
    truth_index: int
    recon_index: int | None
    process_name_similarity: float
    process_alignment_similarity: float
    step_alignments: list[dict[str, Any]]
    exception_alignments: list[dict[str, Any]]
    step_field_similarities: list[FieldSimilarity]
    exception_field_similarities: list[FieldSimilarity]
    missed_steps: list[dict[str, Any]]
    extra_steps: list[dict[str, Any]]
    missed_exceptions: list[dict[str, Any]]
    extra_exceptions: list[dict[str, Any]]
    aggregate_similarity: float


@dataclass
class EmbeddingReport:
    scalar_fields: list[FieldSimilarity]
    process_reports: list[ProcessEmbeddingReport]
    missed_processes: list[dict[str, Any]]
    extra_processes: list[dict[str, Any]]
    overall_similarity: float
    counts: dict[str, int] = field(default_factory=dict)


def _embed_pair_sim(truth: str, recon: str) -> float:
    if not truth.strip() and not recon.strip():
        return 1.0
    if not truth.strip() or not recon.strip():
        return 0.0
    embs = embed_texts([truth, recon])
    return round(cosine_similarity(embs[0], embs[1]), 6)


def _align_to_dict(align: AlignmentResult) -> dict[str, Any]:
    return {
        "pairs": [
            {
                "truth_index": p.truth_index,
                "recon_index": p.recon_index,
                "similarity": p.similarity,
                "truth_text": p.truth_text,
                "recon_text": p.recon_text,
            }
            for p in align.pairs
        ],
        "missed_truth": [{"index": i, "text": t} for i, t in align.missed_truth],
        "extra_recon": [{"index": i, "text": t} for i, t in align.extra_recon],
    }


def _step_field_sims(
    truth_proc,
    recon_proc,
    pair: AlignmentPair,
) -> list[FieldSimilarity]:
    ts = truth_proc.steps[pair.truth_index]
    rs = recon_proc.steps[pair.recon_index]
    prefix = f"steps[{pair.truth_index}]↔[{pair.recon_index}]"
    return [
        FieldSimilarity(f"{prefix}.step_name", ts.step_name, rs.step_name, _embed_pair_sim(ts.step_name, rs.step_name)),
        FieldSimilarity(
            f"{prefix}.software_tools_used",
            ", ".join(ts.software_tools_used),
            ", ".join(rs.software_tools_used),
            _embed_pair_sim(", ".join(ts.software_tools_used), ", ".join(rs.software_tools_used)),
        ),
        FieldSimilarity(f"{prefix}.time_needed", ts.time_needed, rs.time_needed, _embed_pair_sim(ts.time_needed, rs.time_needed)),
        FieldSimilarity(
            f"{prefix}.handoff_to",
            "" if ts.handoff_to is None else str(ts.handoff_to),
            "" if rs.handoff_to is None else str(rs.handoff_to),
            _embed_pair_sim(
                "" if ts.handoff_to is None else str(ts.handoff_to),
                "" if rs.handoff_to is None else str(rs.handoff_to),
            ),
        ),
    ]


def _exception_field_sims(truth_proc, recon_proc, pair: AlignmentPair) -> list[FieldSimilarity]:
    te = truth_proc.exceptions[pair.truth_index]
    re = recon_proc.exceptions[pair.recon_index]
    prefix = f"exceptions[{pair.truth_index}]↔[{pair.recon_index}]"
    return [
        FieldSimilarity(f"{prefix}.what_goes_wrong", te.what_goes_wrong, re.what_goes_wrong, _embed_pair_sim(te.what_goes_wrong, re.what_goes_wrong)),
        FieldSimilarity(f"{prefix}.impact", te.impact, re.impact, _embed_pair_sim(te.impact, re.impact)),
        FieldSimilarity(f"{prefix}.recovery", te.recovery, re.recovery, _embed_pair_sim(te.recovery, re.recovery)),
    ]


def compare_embeddings(
    truth: GroundTruthProfile,
    reconstructed: ReconstructedPersona,
    *,
    min_alignment_similarity: float = 0.0,
) -> EmbeddingReport:
    scalar_fields = [
        FieldSimilarity("name", truth.name, reconstructed.name, _embed_pair_sim(truth.name, reconstructed.name)),
        FieldSimilarity("role", truth.role, reconstructed.role, _embed_pair_sim(truth.role, reconstructed.role)),
    ]

    proc_align = greedy_align(
        process_names(truth),
        process_names(reconstructed),
        min_similarity=min_alignment_similarity,
    )

    process_reports: list[ProcessEmbeddingReport] = []
    all_sims: list[float] = [f.similarity for f in scalar_fields]

    for pair in proc_align.pairs:
        tp = truth.processes[pair.truth_index]
        rp = reconstructed.processes[pair.recon_index]
        pname_sim = pair.similarity

        step_align = greedy_align(
            step_composites(tp),
            step_composites(rp),
            min_similarity=min_alignment_similarity,
        )
        exc_align = greedy_align(
            exception_composites(tp),
            exception_composites(rp),
            min_similarity=min_alignment_similarity,
        )

        step_field_sims: list[FieldSimilarity] = []
        for sp in step_align.pairs:
            step_field_sims.extend(_step_field_sims(tp, rp, sp))
            all_sims.extend(s.similarity for s in step_field_sims[-4:])

        exc_field_sims: list[FieldSimilarity] = []
        for ep in exc_align.pairs:
            exc_field_sims.extend(_exception_field_sims(tp, rp, ep))
            all_sims.extend(s.similarity for s in exc_field_sims[-3:])

        proc_sims = [pname_sim] + [s.similarity for s in step_field_sims] + [s.similarity for s in exc_field_sims]
        proc_agg = sum(proc_sims) / len(proc_sims) if proc_sims else 0.0
        all_sims.append(proc_agg)

        process_reports.append(
            ProcessEmbeddingReport(
                truth_index=pair.truth_index,
                recon_index=pair.recon_index,
                process_name_similarity=pname_sim,
                process_alignment_similarity=pair.similarity,
                step_alignments=_align_to_dict(step_align)["pairs"],
                exception_alignments=_align_to_dict(exc_align)["pairs"],
                step_field_similarities=step_field_sims,
                exception_field_similarities=exc_field_sims,
                missed_steps=_align_to_dict(step_align)["missed_truth"],
                extra_steps=_align_to_dict(step_align)["extra_recon"],
                missed_exceptions=_align_to_dict(exc_align)["missed_truth"],
                extra_exceptions=_align_to_dict(exc_align)["extra_recon"],
                aggregate_similarity=round(proc_agg, 6),
            )
        )

    overall = round(sum(all_sims) / len(all_sims), 6) if all_sims else 0.0

    counts = {
        "missed_processes": len(proc_align.missed_truth),
        "extra_processes": len(proc_align.extra_recon),
        "missed_steps": sum(len(p.missed_steps) for p in process_reports),
        "extra_steps": sum(len(p.extra_steps) for p in process_reports),
        "missed_exceptions": sum(len(p.missed_exceptions) for p in process_reports),
        "extra_exceptions": sum(len(p.extra_exceptions) for p in process_reports),
    }

    return EmbeddingReport(
        scalar_fields=scalar_fields,
        process_reports=process_reports,
        missed_processes=[{"index": i, "text": t} for i, t in proc_align.missed_truth],
        extra_processes=[{"index": i, "text": t} for i, t in proc_align.extra_recon],
        overall_similarity=overall,
        counts=counts,
    )


def embedding_report_to_dict(report: EmbeddingReport) -> dict:
    return {
        "scalar_fields": [
            {
                "path": f.path,
                "truth_text": f.truth_text,
                "recon_text": f.recon_text,
                "similarity": f.similarity,
            }
            for f in report.scalar_fields
        ],
        "process_reports": [
            {
                "truth_index": pr.truth_index,
                "recon_index": pr.recon_index,
                "process_name_similarity": pr.process_name_similarity,
                "aggregate_similarity": pr.aggregate_similarity,
                "step_alignments": pr.step_alignments,
                "exception_alignments": pr.exception_alignments,
                "step_field_similarities": [
                    {"path": s.path, "similarity": s.similarity}
                    for s in pr.step_field_similarities
                ],
                "exception_field_similarities": [
                    {"path": s.path, "similarity": s.similarity}
                    for s in pr.exception_field_similarities
                ],
                "missed_steps": pr.missed_steps,
                "extra_steps": pr.extra_steps,
                "missed_exceptions": pr.missed_exceptions,
                "extra_exceptions": pr.extra_exceptions,
            }
            for pr in report.process_reports
        ],
        "missed_processes": report.missed_processes,
        "extra_processes": report.extra_processes,
        "overall_similarity": report.overall_similarity,
        "counts": report.counts,
    }
