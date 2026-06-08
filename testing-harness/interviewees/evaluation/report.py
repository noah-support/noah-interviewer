"""Format evaluation run summaries for CLI output."""

from __future__ import annotations

from interviewees.evaluation.pipeline import SummaryRow


def _label(row: SummaryRow) -> str:
    if row.run_id:
        return f"{row.run_id}/{row.folder}/{row.system}"
    return f"{row.folder}/{row.system}"


def format_run_report(rows: list[SummaryRow]) -> str:
    """Human-readable summary of ok / skipped / error rows."""
    ok = [r for r in rows if r.status == "ok"]
    skipped = [r for r in rows if r.status == "skipped"]
    errors = [r for r in rows if r.status == "error"]
    other = [r for r in rows if r.status not in ("ok", "skipped", "error")]

    lines: list[str] = []
    lines.append(
        f"Done: {len(ok)}/{len(rows)} ok, {len(skipped)} skipped, {len(errors)} errors"
    )

    if errors:
        lines.append("")
        lines.append("Errors:")
        for row in errors:
            lines.append(f"  [{_label(row)}] {row.error}")

    if skipped:
        lines.append("")
        lines.append("Skipped:")
        for row in skipped:
            lines.append(f"  [{_label(row)}] {row.error}")

    if other:
        lines.append("")
        lines.append("Other:")
        for row in other:
            lines.append(f"  [{_label(row)}] status={row.status} {row.error}".rstrip())

    return "\n".join(lines)
