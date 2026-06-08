"""Human-readable validation.md from validation reports."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from interviewees.evaluation.llm_judge import JUDGE_DIMENSIONS
from interviewees.persona_layout import PERSONA_JSON_FILENAME


def _fmt_scores_table(judge: dict[str, Any]) -> str:
    scores = judge.get("scores") or {}
    justifications = judge.get("justifications") or {}
    lines = ["| Dimension | Score | Justification |", "|-----------|-------|---------------|"]
    for dim in JUDGE_DIMENSIONS:
        score = scores.get(dim, "—")
        just = (justifications.get(dim) or "").replace("|", "\\|")
        label = dim.replace("_", " ").title()
        lines.append(f"| {label} | {score} | {just} |")
    return "\n".join(lines)


def _fmt_alignment_compact(embeddings: dict[str, Any]) -> str:
    parts: list[str] = []
    overall = embeddings.get("overall_similarity")
    parts.append(f"**Overall embedding similarity:** {overall}")
    counts = embeddings.get("counts") or {}
    parts.append(
        f"**Unmatched counts:** processes missed={counts.get('missed_processes', 0)}, "
        f"extra={counts.get('extra_processes', 0)}; "
        f"steps missed={counts.get('missed_steps', 0)}, extra={counts.get('extra_steps', 0)}; "
        f"exceptions missed={counts.get('missed_exceptions', 0)}, "
        f"extra={counts.get('extra_exceptions', 0)}"
    )
    for pr in embeddings.get("process_reports") or []:
        ti = pr.get("truth_index")
        ri = pr.get("recon_index")
        agg = pr.get("aggregate_similarity")
        parts.append(f"\n### Process alignment (truth[{ti}] ↔ recon[{ri}], aggregate={agg})")
        for sp in pr.get("step_alignments") or []:
            parts.append(
                f"- Step: \"{sp.get('truth_text', '')[:60]}\" ↔ "
                f"\"{sp.get('recon_text', '')[:60]}\" (sim={sp.get('similarity')})"
            )
        for ms in pr.get("missed_steps") or []:
            parts.append(f"- Missed step: \"{ms.get('text', '')[:80]}\"")
        for es in pr.get("extra_steps") or []:
            parts.append(f"- Extra step: \"{es.get('text', '')[:80]}\"")
        for ep in pr.get("exception_alignments") or []:
            parts.append(
                f"- Exception: \"{ep.get('truth_text', '')[:50]}\" ↔ "
                f"\"{ep.get('recon_text', '')[:50]}\" (sim={ep.get('similarity')})"
            )
        for me in pr.get("missed_exceptions") or []:
            parts.append(f"- Missed exception: \"{me.get('text', '')[:80]}\"")
        for ee in pr.get("extra_exceptions") or []:
            parts.append(f"- Extra exception: \"{ee.get('text', '')[:80]}\"")
    missed_p = embeddings.get("missed_processes") or []
    extra_p = embeddings.get("extra_processes") or []
    for m in missed_p:
        parts.append(f"- Missed process: \"{m.get('text', '')}\"")
    for e in extra_p:
        parts.append(f"- Extra process: \"{e.get('text', '')}\"")
    return "\n".join(parts)


def render_validation_markdown(
    folder_name: str,
    reports_by_system: dict[str, dict[str, Any]],
    *,
    run_id: str = "",
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = (
        f"# Validation report — {run_id} / persona {folder_name}"
        if run_id
        else f"# Validation report — persona {folder_name}"
    )
    lines = [
        title,
        "",
        f"Generated: {ts}",
        "",
    ]
    if run_id:
        lines.append(f"**Run:** `{run_id}`")
        sample = next(iter(reports_by_system.values()), {})
        if sample.get("input_dir"):
            lines.append(f"**Input:** `{sample['input_dir']}`")
        if sample.get("output_dir"):
            lines.append(f"**Output:** `{sample['output_dir']}`")
        lines.append("")
    lines.extend(
        [
            f"Ground truth: `{PERSONA_JSON_FILENAME}` (backstory ignored for scoring).",
            "",
        ]
    )
    for system in ("noah", "elevenlabs"):
        report = reports_by_system.get(system)
        if not report:
            continue
        title = "Noah" if system == "noah" else "ElevenLabs"
        lines.extend([f"## {title}", ""])
        recon_file = report.get("reconstruction_file", f"result_{system}.json")
        lines.append(f"Reconstruction: `{recon_file}`")
        embeddings = report.get("embeddings") or {}
        judge = report.get("judge") or {}
        lines.append("")
        lines.append(_fmt_alignment_compact(embeddings))
        lines.append("")
        lines.append("### LLM judge (1–5)")
        lines.append("")
        lines.append(_fmt_scores_table(judge))
        lines.append("")
    lines.extend(
        [
            "---",
            "",
            "*Embedding similarity uses greedy alignment by cosine similarity on field text. "
            "Judge scores are from a separate LLM comparison.*",
        ]
    )
    return "\n".join(lines)


def write_validation_markdown(
    folder: Path,
    reports_by_system: dict[str, dict[str, Any]],
    *,
    force: bool = False,
    run_id: str = "",
) -> Path:
    from interviewees.evaluation.io import write_text
    from interviewees.persona_layout import validation_md_in_folder

    path = validation_md_in_folder(folder)
    content = render_validation_markdown(folder.name, reports_by_system, run_id=run_id)
    write_text(path, content + "\n", force=force)
    return path
