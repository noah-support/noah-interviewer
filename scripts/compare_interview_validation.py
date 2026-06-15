"""Compare Noah vs ElevenLabs interview extraction quality from validation summaries."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "testing-harness/results/validation/analysis_report.md"

ALPHA = 0.05
RANDOM_SEED = 42
BOOTSTRAP_N_RESAMPLES = 5000
BOOTSTRAP_CONFIDENCE = 0.95
RESEARCH_QUESTION = (
    "Is the Noah interview system significantly better than the ElevenLabs interviewer?"
)

# Directional H₁ (Noah > ElevenLabs) was committed in the analysis plan before
# inspecting validation outcomes. Use --two-sided for a sensitivity analysis.
DIRECTION_PRE_SPECIFIED = True

JUDGE_DIMENSIONS = [
    "activity_coverage",
    "control_flow_and_handoff_fidelity",
    "attribute_accuracy",
    "exception_and_edge_case_capture",
    "faithfulness_no_hallucination",
]

CORE_METRICS = ["overall_embedding_similarity", *JUDGE_DIMENSIONS]
ERROR_METRICS = ["total_missed", "total_extra"]
TEST_METRICS = [*CORE_METRICS, *ERROR_METRICS]
DESCRIPTIVE_METRICS = TEST_METRICS

ORDINAL_METRICS = set(JUDGE_DIMENSIONS)
CONTINUOUS_METRICS = {"overall_embedding_similarity"}
COUNT_METRICS = set(ERROR_METRICS)

ERROR_COLS = [
    "missed_processes",
    "extra_processes",
    "missed_steps",
    "extra_steps",
    "missed_exceptions",
    "extra_exceptions",
]

METRIC_LABELS = {
    "overall_embedding_similarity": "Overall Embedding Similarity",
    "activity_coverage": "Activity Coverage",
    "control_flow_and_handoff_fidelity": "Control Flow & Handoff Fidelity",
    "attribute_accuracy": "Attribute Accuracy",
    "exception_and_edge_case_capture": "Exception & Edge Case Capture",
    "faithfulness_no_hallucination": "Faithfulness (No Hallucination)",
    "total_missed": "Total Missed Items",
    "total_extra": "Total Extra / Hallucinated Items",
}

HIGHER_NOAH_BETTER = {
    "overall_embedding_similarity": True,
    "activity_coverage": True,
    "control_flow_and_handoff_fidelity": True,
    "attribute_accuracy": True,
    "exception_and_edge_case_capture": True,
    "faithfulness_no_hallucination": True,
    "total_missed": False,
    "total_extra": False,
}

PAIR_KEY = ["run_id", "folder"]
SYSTEMS = ("noah", "elevenlabs")

# Oriented rank-biserial magnitudes below this are treated as a genuine tie.
RBC_TIE_THRESHOLD = 0.1

PERMUTATION_P_FLOOR = 1 / 256  # one-sided exact sign-flip with n=8 pairs

TRANSCRIPT_DISCUSSION = """\
### Transcript task alignment

The two systems are not conducting identical interviews against the same scoring rubric in the same way. Noah's transcript is structured process mapping (steps, tools, handoffs, exceptions), while the ElevenLabs transcript is a general work interview (time estimates, frustrations, ambitions). The validation pipeline measures **process-reconstruction fidelity**, so ElevenLabs is partly penalized for not attempting structured extraction.

That may be exactly the thesis point — a purpose-built interviewer beats a generic one — but readers should not over-read these numbers as pure "Noah model vs ElevenLabs model" platform quality. The comparison reflects **configuration-for-task** as much as underlying capability.

### Error-count trade-off

Paired testing on error counts surfaces an honest trade-off: Noah tends to **miss fewer** ground-truth items (rank-based lead on missed items) but is **worse on precision** (oriented rank-biserial negative on extra/hallucinated items, despite a lower median driven by skew). That pattern is practically meaningful even when judge scores are flat — it suggests Noah extracts more aggressively, which helps recall but hurts precision."""


def discover_summaries(root: Path) -> list[Path]:
    return sorted(root.rglob("validation_summary.json"))


def _infer_run_id(row: dict, summary_path: Path) -> str:
    run_id = row.get("run_id") or ""
    if run_id:
        return str(run_id)
    parent = summary_path.parent.name
    if parent.startswith("run_"):
        return parent
    file_run_id = json.loads(summary_path.read_text(encoding="utf-8")).get("run_id", "")
    return str(file_run_id) if file_run_id else parent


def _build_dataframe(raw_rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(raw_rows)
    if "status" not in df.columns:
        df["status"] = "ok"
    if "error" not in df.columns:
        df["error"] = ""

    numeric_cols = [
        "overall_embedding_similarity",
        *JUDGE_DIMENSIONS,
        *ERROR_COLS,
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["total_missed"] = df[
        ["missed_processes", "missed_steps", "missed_exceptions"]
    ].fillna(0).sum(axis=1)
    df["total_extra"] = df[
        ["extra_processes", "extra_steps", "extra_exceptions"]
    ].fillna(0).sum(axis=1)
    return df


def summarize_non_ok_rows(df: pd.DataFrame) -> dict[str, list[dict[str, str]]]:
    non_ok = df[df["status"] != "ok"]
    summary: dict[str, list[dict[str, str]]] = {system: [] for system in SYSTEMS}
    for _, row in non_ok.iterrows():
        system = str(row.get("system", ""))
        if system not in summary:
            continue
        reason = str(row.get("error", "")).strip() or "(no error message)"
        summary[system].append(
            {
                "run_id": str(row.get("run_id", "")),
                "folder": str(row.get("folder", "")),
                "status": str(row.get("status", "")),
                "reason": reason,
            }
        )
    return summary


def format_non_ok_summary(
    non_ok_summary: dict[str, list[dict[str, str]]],
    *,
    included_in_analysis: bool,
) -> str:
    action = "included in" if included_in_analysis else "excluded from"
    total = sum(len(entries) for entries in non_ok_summary.values())
    if total == 0:
        return "No non-ok rows found."

    lines = [
        f"Non-ok rows {action} analysis: {total} total",
    ]
    for system in SYSTEMS:
        entries = non_ok_summary[system]
        lines.append(f"\n{system}: {len(entries)}")
        if not entries:
            lines.append("  (none)")
            continue
        for entry in entries:
            location = f"{entry['run_id']}/{entry['folder']}".strip("/")
            lines.append(
                f"  - [{entry['status']}] {location} — {entry['reason']}"
            )
    return "\n".join(lines)


def format_non_ok_summary_markdown(
    non_ok_summary: dict[str, list[dict[str, str]]],
    *,
    included_in_analysis: bool,
) -> str:
    total = sum(len(entries) for entries in non_ok_summary.values())
    if total == 0:
        return "No non-ok rows found."

    action = "included in" if included_in_analysis else "excluded from"
    lines = [f"{total} non-ok row(s) {action} this analysis.", ""]
    for system in SYSTEMS:
        entries = non_ok_summary[system]
        lines.append(f"**{system}:** {len(entries)}")
        if not entries:
            lines.append("")
            continue
        for entry in entries:
            location = f"{entry['run_id']}/{entry['folder']}".strip("/")
            lines.append(
                f"- `[{entry['status']}]` {location} — {entry['reason']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def print_non_ok_summary(
    non_ok_summary: dict[str, list[dict[str, str]]],
    *,
    included_in_analysis: bool,
) -> None:
    print(f"\n{format_non_ok_summary(non_ok_summary, included_in_analysis=included_in_analysis)}")


def load_validation_data(
    root: Path,
    *,
    include_non_ok: bool = False,
) -> tuple[pd.DataFrame, dict[str, list[dict[str, str]]], list[Path]]:
    summary_paths = discover_summaries(root)
    if not summary_paths:
        raise FileNotFoundError(
            f"No validation_summary.json files found under {root}"
        )

    raw_rows: list[dict] = []
    for path in summary_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("rows", []):
            enriched = dict(row)
            enriched["run_id"] = _infer_run_id(row, path)
            enriched["_source_file"] = str(path.relative_to(root))
            raw_rows.append(enriched)

    df_all = _build_dataframe(raw_rows)
    df_all = df_all[df_all["system"].isin(SYSTEMS)].copy()
    non_ok_summary = summarize_non_ok_rows(df_all)

    if include_non_ok:
        df = df_all.copy()
    else:
        df = df_all[df_all["status"] == "ok"].copy()

    return df.reset_index(drop=True), non_ok_summary, summary_paths


def extract_paired_values(
    df: pd.DataFrame,
    metric: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return aligned Noah values, ElevenLabs values, and signed diffs (Noah better > 0)."""
    higher_noah_better = HIGHER_NOAH_BETTER[metric]
    noah_vals: list[float] = []
    el_vals: list[float] = []
    diffs: list[float] = []

    for _, group in df.groupby(PAIR_KEY, sort=True):
        noah_rows = group[group["system"] == "noah"]
        el_rows = group[group["system"] == "elevenlabs"]
        if len(noah_rows) != 1 or len(el_rows) != 1:
            continue
        nv = noah_rows[metric].iloc[0]
        ev = el_rows[metric].iloc[0]
        if pd.isna(nv) or pd.isna(ev):
            continue
        nv_f = float(nv)
        ev_f = float(ev)
        delta = nv_f - ev_f
        if not higher_noah_better:
            delta = -delta
        noah_vals.append(nv_f)
        el_vals.append(ev_f)
        diffs.append(delta)

    return (
        np.asarray(noah_vals, dtype=float),
        np.asarray(el_vals, dtype=float),
        np.asarray(diffs, dtype=float),
    )


def _iqr(vals: pd.Series) -> float:
    if vals.empty:
        return np.nan
    q1 = float(vals.quantile(0.25))
    q3 = float(vals.quantile(0.75))
    return q3 - q1


def _summary_noah_leads(
    noah_summary: float,
    el_summary: float,
    *,
    higher_noah_better: bool,
) -> str:
    """Median/mean-based lead for display comparison only (not the directional call)."""
    if np.isnan(noah_summary) or np.isnan(el_summary):
        return "n/a"
    if noah_summary == el_summary:
        return "tie"
    if (noah_summary > el_summary) == higher_noah_better:
        return "yes"
    return "no"


def noah_leads_from_oriented_r(rank_biserial: float) -> str:
    """Rank-based directional call; r is oriented so positive means Noah better."""
    if np.isnan(rank_biserial):
        return "n/a"
    if abs(rank_biserial) < RBC_TIE_THRESHOLD:
        return "tie"
    if rank_biserial > 0:
        return "yes"
    return "no"


def _lead_disagreement_note(rank_lead: str, summary_lead: str) -> str:
    if rank_lead in ("n/a",) or summary_lead in ("n/a",):
        return ""
    if rank_lead == summary_lead:
        return ""
    return " (median differs due to ties/skew)"


def compute_descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Median/IQR for ordinal and count metrics; mean/std for continuous embedding."""
    rows: list[dict] = []
    for metric in DESCRIPTIVE_METRICS:
        higher_noah_better = HIGHER_NOAH_BETTER[metric]
        noah_series = df.loc[df["system"] == "noah", metric].dropna()
        el_series = df.loc[df["system"] == "elevenlabs", metric].dropna()

        row: dict[str, object] = {
            "metric": metric,
            "label": METRIC_LABELS[metric],
            "summary_type": (
                "mean_std"
                if metric in CONTINUOUS_METRICS
                else "median_iqr"
            ),
            "noah_n": int(len(noah_series)),
            "elevenlabs_n": int(len(el_series)),
        }

        if metric in CONTINUOUS_METRICS:
            noah_summary = float(noah_series.mean()) if len(noah_series) else np.nan
            el_summary = float(el_series.mean()) if len(el_series) else np.nan
            noah_spread = float(noah_series.std(ddof=1)) if len(noah_series) > 1 else np.nan
            el_spread = float(el_series.std(ddof=1)) if len(el_series) > 1 else np.nan
            row.update(
                {
                    "noah_center": noah_summary,
                    "noah_spread": noah_spread,
                    "elevenlabs_center": el_summary,
                    "elevenlabs_spread": el_spread,
                }
            )
        else:
            noah_summary = float(noah_series.median()) if len(noah_series) else np.nan
            el_summary = float(el_series.median()) if len(el_series) else np.nan
            noah_spread = _iqr(noah_series)
            el_spread = _iqr(el_series)
            row.update(
                {
                    "noah_center": noah_summary,
                    "noah_spread": noah_spread,
                    "elevenlabs_center": el_summary,
                    "elevenlabs_spread": el_spread,
                }
            )

        rows.append(row)
    return pd.DataFrame(rows)


def merge_desc_with_rank_calls(
    desc: pd.DataFrame,
    test_results: pd.DataFrame,
) -> pd.DataFrame:
    """Attach rank-based lead calls and median/summary disagreement notes."""
    merged = desc.merge(
        test_results[
            ["metric", "rank_biserial", "noah_leads", "n_wilcoxon_nonzero"]
        ],
        on="metric",
        how="left",
    )
    merged["summary_noah_leads"] = merged.apply(
        lambda r: _summary_noah_leads(
            r["noah_center"],
            r["elevenlabs_center"],
            higher_noah_better=HIGHER_NOAH_BETTER[r["metric"]],
        ),
        axis=1,
    )
    merged["lead_note"] = merged.apply(
        lambda r: _lead_disagreement_note(r["noah_leads"], r["summary_noah_leads"]),
        axis=1,
    )
    merged["noah_leads_display"] = merged.apply(
        lambda r: (
            "n/a"
            if r["noah_leads"] == "n/a"
            else r["noah_leads"] + r["lead_note"]
        ),
        axis=1,
    )
    return merged


def matched_pairs_rank_biserial(diffs: np.ndarray) -> float:
    """Signed matched-pairs rank-biserial correlation (positive = Noah better)."""
    nonzero = diffs[diffs != 0]
    n = len(nonzero)
    if n == 0:
        return np.nan
    ranks = stats.rankdata(np.abs(nonzero))
    w_plus = ranks[nonzero > 0].sum()
    w_minus = ranks[nonzero < 0].sum()
    denom = w_plus + w_minus
    if denom == 0:
        return 0.0
    return float((w_plus - w_minus) / denom)


def bootstrap_matched_rbc_ci(
    diffs: np.ndarray,
    *,
    n_resamples: int = BOOTSTRAP_N_RESAMPLES,
    confidence_level: float = BOOTSTRAP_CONFIDENCE,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    """95% percentile bootstrap CI for matched-pairs rank-biserial correlation."""
    diffs = np.asarray(diffs, dtype=float)
    if len(diffs) < 2:
        return np.nan, np.nan

    boot_rng = rng or np.random.default_rng(RANDOM_SEED)
    n = len(diffs)
    boot_stats = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        boot_diffs = diffs[boot_rng.integers(0, n, size=n)]
        boot_stats[i] = matched_pairs_rank_biserial(boot_diffs)

    alpha = 1.0 - confidence_level
    lo, hi = np.nanpercentile(boot_stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def _format_rbc_with_ci(
    rbc: float,
    ci_lower: float,
    ci_upper: float,
) -> str:
    if np.isnan(rbc):
        return "n/a"
    if np.isnan(ci_lower) or np.isnan(ci_upper):
        return f"{rbc:.3f}"
    return f"{rbc:.3f} [{ci_lower:.3f}, {ci_upper:.3f}]"


def exact_sign_flip_pvalue(
    diffs: np.ndarray,
    *,
    alternative: str,
) -> float:
    """Enumerate all 2^n sign-flips; no asymptotic approximation."""
    n = len(diffs)
    if n == 0:
        return np.nan
    if n > 20:
        raise ValueError(f"Exact permutation limited to n<=20, got {n}")

    observed = float(diffs.sum())
    extremes = 0
    total = 2**n
    for signs in product((-1.0, 1.0), repeat=n):
        stat = float(np.dot(signs, diffs))
        if alternative == "greater":
            if stat >= observed - 1e-12:
                extremes += 1
        elif alternative == "less":
            if stat <= observed + 1e-12:
                extremes += 1
        elif alternative == "two-sided":
            if abs(stat) >= abs(observed) - 1e-12:
                extremes += 1
        else:
            raise ValueError(f"Unknown alternative: {alternative}")
    return extremes / total


def wilcoxon_exact_pvalue(
    diffs: np.ndarray,
    *,
    alternative: str,
) -> float:
    nonzero = diffs[diffs != 0]
    if len(nonzero) < 1:
        return np.nan
    return float(
        stats.wilcoxon(
            nonzero,
            alternative=alternative,
            method="exact",
            zero_method="wilcox",
        ).pvalue
    )


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    pvals = np.asarray(pvals, dtype=float)
    out = np.full_like(pvals, np.nan)
    valid = ~np.isnan(pvals)
    if valid.sum() == 0:
        return out
    m = int(valid.sum())
    ordered_idx = np.where(valid)[0]
    sorted_p = pvals[ordered_idx]
    order = np.argsort(sorted_p)
    ranked = sorted_p[order]
    adjusted = np.minimum.accumulate(
        (ranked * m / np.arange(1, m + 1))[::-1]
    )[::-1]
    adjusted = np.minimum(adjusted, 1.0)
    restored = np.empty(m)
    restored[order] = adjusted
    out[ordered_idx] = restored
    return out


def run_paired_tests(
    df: pd.DataFrame,
    *,
    alternative: str,
) -> pd.DataFrame:
    rows: list[dict] = []
    for metric in TEST_METRICS:
        noah_vals, el_vals, diffs = extract_paired_values(df, metric)
        n_pairs = len(diffs)

        noah_center = float(np.median(noah_vals)) if n_pairs else np.nan
        el_center = float(np.median(el_vals)) if n_pairs else np.nan
        if metric in CONTINUOUS_METRICS and n_pairs:
            noah_center = float(np.mean(noah_vals))
            el_center = float(np.mean(el_vals))

        if n_pairs < 2:
            rows.append(
                {
                    "metric": metric,
                    "label": METRIC_LABELS[metric],
                    "n_pairs": n_pairs,
                    "n_wilcoxon_nonzero": int(np.sum(diffs != 0)),
                    "noah_center": noah_center,
                    "elevenlabs_center": el_center,
                    "p_raw": np.nan,
                    "p_wilcoxon": np.nan,
                    "rank_biserial": np.nan,
                    "rbc_ci_lower": np.nan,
                    "rbc_ci_upper": np.nan,
                    "noah_leads": "n/a",
                    "noah_significantly_better": "insufficient_data",
                }
            )
            continue

        p_perm = exact_sign_flip_pvalue(diffs, alternative=alternative)
        p_wilcox = wilcoxon_exact_pvalue(diffs, alternative=alternative)
        rbc = matched_pairs_rank_biserial(diffs)
        rbc_ci_lower, rbc_ci_upper = bootstrap_matched_rbc_ci(diffs)
        noah_leads = noah_leads_from_oriented_r(rbc)

        rows.append(
            {
                "metric": metric,
                "label": METRIC_LABELS[metric],
                "n_pairs": n_pairs,
                "n_wilcoxon_nonzero": int(np.sum(diffs != 0)),
                "noah_center": noah_center,
                "elevenlabs_center": el_center,
                "p_raw": p_perm,
                "p_wilcoxon": p_wilcox,
                "rank_biserial": rbc,
                "rbc_ci_lower": rbc_ci_lower,
                "rbc_ci_upper": rbc_ci_upper,
                "noah_leads": noah_leads,
                "noah_significantly_better": (
                    "yes"
                    if p_perm < ALPHA and noah_leads == "yes"
                    else "no"
                ),
            }
        )
    results = pd.DataFrame(rows)
    return apply_fdr(results)


def apply_fdr(results: pd.DataFrame) -> pd.DataFrame:
    out = results.copy()
    pvals = out["p_raw"].to_numpy(dtype=float)
    out["p_fdr"] = benjamini_hochberg(pvals)
    out["sig_fdr"] = out["p_fdr"] < ALPHA
    out["noah_significantly_better_fdr"] = np.where(
        out["noah_significantly_better"] == "yes",
        np.where(out["sig_fdr"], "yes", "no"),
        out["noah_significantly_better"],
    )
    return out


def _format_float(value: float, decimals: int = 4) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"{value:.{decimals}f}"


def _dataframe_to_markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for _, row in df.iterrows():
        cells = [str(row[col]) for col in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _format_descriptive_cell(row: pd.Series, system: str) -> str:
    center = row[f"{system}_center"]
    spread = row[f"{system}_spread"]
    n = row[f"{system}_n"]
    if row["summary_type"] == "mean_std":
        return f"{_format_float(center)} ± {_format_float(spread)} (n={n})"
    return f"median {_format_float(center, 1)}, IQR {_format_float(spread, 1)} (n={n})"


def build_verdict(
    test_results: pd.DataFrame,
    *,
    alternative: str,
) -> str:
    sig_fdr: list[str] = []
    sig_raw_only: list[str] = []
    descriptive_only: list[str] = []
    no_advantage: list[str] = []
    insufficient: list[str] = []

    for _, row in test_results.iterrows():
        label = row["label"]
        rbc = _format_rbc_with_ci(
            row["rank_biserial"],
            row["rbc_ci_lower"],
            row["rbc_ci_upper"],
        )
        if row["noah_significantly_better"] == "insufficient_data":
            insufficient.append(label)
            continue

        p_raw = _format_float(row["p_raw"])
        p_fdr = _format_float(row["p_fdr"])

        if row["noah_significantly_better_fdr"] == "yes":
            sig_fdr.append(f"{label} (r={rbc}, p_fdr={p_fdr})")
        elif row["noah_significantly_better"] == "yes":
            sig_raw_only.append(f"{label} (r={rbc}, p_raw={p_raw}, p_fdr={p_fdr})")
        elif row["noah_leads"] == "yes":
            descriptive_only.append(f"{label} (r={rbc}, p_raw={p_raw})")
        elif row["noah_leads"] == "tie":
            no_advantage.append(f"{label} (tie, r={rbc}, p_raw={p_raw})")
        else:
            no_advantage.append(f"{label} (r={rbc}, p_raw={p_raw})")

    testable = test_results[
        test_results["noah_significantly_better"] != "insufficient_data"
    ]
    n_sig_fdr = len(sig_fdr)
    n_testable = len(testable)

    if n_testable == 0:
        overall = (
            "Inconclusive — not enough paired observations to test whether "
            "Noah is better."
        )
    elif n_sig_fdr == 0:
        overall = (
            "No — after paired testing and Benjamini-Hochberg FDR correction, "
            "we cannot conclude that Noah is significantly better than "
            "ElevenLabs on any tested metric. This does **not** mean the "
            "systems are equivalent: with n=8 pairs the analysis is "
            "underpowered and 'not significant' means the test could not "
            "detect a difference, not that none exists."
        )
    elif n_sig_fdr == n_testable:
        overall = (
            "Yes — Noah is significantly better than ElevenLabs on all tested "
            "metrics (FDR-corrected)."
        )
    else:
        overall = (
            f"Partially — Noah is significantly better on {n_sig_fdr} of "
            f"{n_testable} tested metrics after FDR correction."
        )

    alt_label = {
        "greater": "one-sided (H₁: Noah > ElevenLabs)",
        "two-sided": "two-sided",
        "less": "one-sided (H₁: Noah < ElevenLabs)",
    }[alternative]

    direction_note = (
        "The directional hypothesis (Noah > ElevenLabs) was pre-specified in "
        "the analysis plan before inspecting validation outcomes."
        if alternative == "greater" and DIRECTION_PRE_SPECIFIED
        else (
            "Two-sided tests were used; no directional claim was pre-specified."
            if alternative == "two-sided"
            else "Directional hypothesis as configured."
        )
    )

    parts: list[str] = [
        f"**Research question:** {RESEARCH_QUESTION}",
        f"**Answer:** {overall}",
        (
            "Tests: paired exact sign-flip permutation on matched "
            f"(run_id, persona) differences; {alt_label}; α = {ALPHA}. "
            "Wilcoxon signed-rank (exact) p-values are reported for cross-check. "
            "Benjamini-Hochberg FDR is applied across all eight tested metrics "
            "(six core + two error counts), consistent with the UX survey pipeline."
        ),
        direction_note,
        (
            "Effect sizes: matched-pairs rank-biserial correlation (r) with 95% "
            "percentile bootstrap CI, oriented so positive means Noah better. "
            "Directional lead/no-lead groupings follow the sign of r, not the median."
        ),
        (
            f"Limitation (permutation granularity): with 8 pairs the one-sided exact "
            f"permutation p-value has a floor of 1/256 (≈{PERMUTATION_P_FLOOR:.4f}). "
            "Many ordinal judge-score paired differences are zero (e.g. Faithfulness, "
            "where ElevenLabs has zero IQR), so the number of distinguishable sign "
            "patterns is smaller still and achievable p-values are coarser. This "
            "granularity, not only the small sample, is part of why no metric "
            "reaches significance."
        ),
        (
            "Limitation (Wilcoxon cross-check): the exact Wilcoxon signed-rank "
            "p-values drop zero-difference pairs, so the effective pair count is "
            "below 8 for several metrics (see n_wilcoxon in the test table). "
            "Wilcoxon is reported only as a cross-check, not the primary result."
        ),
    ]

    if sig_fdr:
        parts.append(
            f"Noah is significantly better after FDR on: {', '.join(sig_fdr)}."
        )
    if sig_raw_only:
        parts.append(
            "Significant uncorrected only (not after FDR): "
            f"{', '.join(sig_raw_only)}."
        )
    if descriptive_only:
        parts.append(
            "Noah leads (rank-based) but not significantly on: "
            f"{', '.join(descriptive_only)}."
        )
    if no_advantage:
        parts.append(
            "Noah does not lead (rank-based), or is tied, on: "
            f"{', '.join(no_advantage)}."
        )
    if insufficient:
        parts.append(f"Insufficient paired data: {', '.join(insufficient)}.")

    return "\n\n".join(parts)


def print_descriptive_table(desc_with_leads: pd.DataFrame) -> None:
    print(
        "\nContinuous metrics: mean ± std. "
        "Ordinal/count metrics: median, IQR. "
        "Noah leads? is rank-based (oriented r sign)."
    )
    print(
        f"\n{'Metric':<42} {'Noah':>28} {'ElevenLabs':>28} {'Noah leads?':>22}"
    )
    print("-" * 122)
    for _, row in desc_with_leads.iterrows():
        noah = _format_descriptive_cell(row, "noah")
        el = _format_descriptive_cell(row, "elevenlabs")
        print(
            f"{row['label']:<42} {noah:>28} {el:>28} "
            f"{row['noah_leads_display']:>22}"
        )


def print_test_table(test_results: pd.DataFrame) -> None:
    print(f"\nResearch question: {RESEARCH_QUESTION}")
    print(
        f"\n{'Metric':<36} {'n':>3} {'r [95% CI]':>22} "
        f"{'p_perm':>8} {'p_fdr':>8} {'Sig(FDR)':>9}"
    )
    print("-" * 92)
    for _, row in test_results.iterrows():
        if row["noah_significantly_better"] == "insufficient_data":
            rbc = p_perm = p_fdr = sig = "n/a"
        else:
            rbc = _format_rbc_with_ci(
                row["rank_biserial"],
                row["rbc_ci_lower"],
                row["rbc_ci_upper"],
            )
            p_perm = _format_float(row["p_raw"])
            p_fdr = _format_float(row["p_fdr"])
            sig = "Yes" if row["noah_significantly_better_fdr"] == "yes" else "No"
        print(
            f"{row['label']:<36} {row['n_pairs']:>3} {rbc:>22} "
            f"{p_perm:>8} {p_fdr:>8} {sig:>9}"
        )


def write_markdown_report(
    *,
    output_path: Path,
    summary_paths: list[Path],
    search_root: Path,
    df: pd.DataFrame,
    non_ok_summary: dict[str, list[dict[str, str]]],
    include_non_ok: bool,
    desc_with_leads: pd.DataFrame,
    test_results: pd.DataFrame,
    verdict: str,
    alternative: str,
) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sources = "\n".join(
        f"- `{p.relative_to(search_root)}`" for p in summary_paths
    )

    desc_display = desc_with_leads.copy()
    desc_display["noah"] = desc_display.apply(
        lambda r: _format_descriptive_cell(r, "noah"), axis=1
    )
    desc_display["elevenlabs"] = desc_display.apply(
        lambda r: _format_descriptive_cell(r, "elevenlabs"), axis=1
    )

    embedding_desc = desc_display[
        desc_display["metric"].isin(CONTINUOUS_METRICS)
    ][["label", "noah", "elevenlabs", "noah_leads_display"]].rename(
        columns={"noah_leads_display": "noah_leads_rank_based"}
    )

    ordinal_desc = desc_display[
        desc_display["metric"].isin(ORDINAL_METRICS)
    ][["label", "noah", "elevenlabs", "noah_leads_display"]].rename(
        columns={"noah_leads_display": "noah_leads_rank_based"}
    )

    error_desc = desc_display[
        desc_display["metric"].isin(COUNT_METRICS)
    ][["label", "noah", "elevenlabs", "noah_leads_display"]].rename(
        columns={"noah_leads_display": "noah_leads_rank_based"}
    )

    test_display = test_results.copy()
    test_display = test_display.rename(columns={"n_wilcoxon_nonzero": "n_wilcoxon"})
    test_display["rank_biserial"] = test_display.apply(
        lambda r: _format_rbc_with_ci(
            r["rank_biserial"],
            r["rbc_ci_lower"],
            r["rbc_ci_upper"],
        ),
        axis=1,
    )
    for col in ("p_raw", "p_wilcoxon", "p_fdr"):
        test_display[col] = test_display[col].apply(
            lambda v: _format_float(v) if pd.notna(v) else "n/a"
        )
    test_display["noah_significantly_better_fdr"] = test_display[
        "noah_significantly_better_fdr"
    ].map({"yes": "Yes", "no": "No", "insufficient_data": "N/A"})

    runs = ", ".join(sorted(df["run_id"].unique()))
    personas = ", ".join(sorted(df["folder"].unique()))
    non_ok_section = format_non_ok_summary_markdown(
        non_ok_summary,
        included_in_analysis=include_non_ok,
    )
    non_ok_heading = (
        "Non-ok rows (included in analysis)"
        if include_non_ok
        else "Non-ok rows (excluded from analysis)"
    )

    alt_label = {
        "greater": "one-sided: Noah > ElevenLabs (pre-specified)",
        "two-sided": "two-sided",
        "less": "one-sided: Noah < ElevenLabs",
    }[alternative]

    content = f"""# Interview Validation Comparison Report

Generated: {timestamp}

## Data sources

Search root: `{search_root}`

{sources}

## Sample

- Paired observations: {test_results['n_pairs'].max() if len(test_results) else 0} complete (run_id, persona) pairs per metric
- Total rows in analysis set: {len(df)}
- Runs: {runs}
- Personas: {personas}

## {non_ok_heading}

{non_ok_section}

## Descriptive statistics

Judge scores (1–5 ordinal): **median and IQR** per system. Embedding similarity (continuous): **mean ± std**. **Noah leads?** follows the oriented rank-biserial sign (rank-based); parenthetical notes flag where the median/mean impression differs due to ties or skew.

### Core metrics

{_dataframe_to_markdown_table(embedding_desc, ['label', 'noah', 'elevenlabs', 'noah_leads_rank_based'])}

{_dataframe_to_markdown_table(ordinal_desc, ['label', 'noah', 'elevenlabs', 'noah_leads_rank_based'])}

### Error counts

{_dataframe_to_markdown_table(error_desc, ['label', 'noah', 'elevenlabs', 'noah_leads_rank_based'])}

## Research question

{RESEARCH_QUESTION}

## Paired tests ({alt_label}, α = {ALPHA})

Matched pairs: each (run_id, persona) contributes one Noah and one ElevenLabs score against the same ground truth. Primary p-value: **exact sign-flip permutation** (enumerates all 2^n sign patterns; no asymptotic approximation). Cross-check: exact Wilcoxon signed-rank (drops zero-difference pairs; see `n_wilcoxon`). Effect size: **matched-pairs rank-biserial correlation** with 95% percentile bootstrap CI (resample pairs with replacement). Multiplicity: **Benjamini-Hochberg FDR** across eight metrics.

{_dataframe_to_markdown_table(test_display, ['label', 'n_pairs', 'n_wilcoxon', 'p_raw', 'p_wilcoxon', 'p_fdr', 'rank_biserial', 'noah_significantly_better_fdr'])}

## Verdict

{verdict}

## Discussion

{TRANSCRIPT_DISCUSSION}
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Noah vs ElevenLabs validation metrics (paired analysis)."
    )
    parser.add_argument(
        "--search-root",
        type=Path,
        default=REPO_ROOT,
        help="Root directory to recursively search for validation_summary.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for the markdown analysis report",
    )
    parser.add_argument(
        "--include-non-ok",
        action="store_true",
        help="Include rows where status is not 'ok'",
    )
    parser.add_argument(
        "--two-sided",
        action="store_true",
        help="Use two-sided tests instead of pre-specified one-sided (Noah > ElevenLabs)",
    )
    args = parser.parse_args()
    alternative = "two-sided" if args.two_sided else "greater"

    search_root = args.search_root.resolve()

    print("=" * 60)
    print("Phase 1: Data ingestion")
    print("=" * 60)
    df, non_ok_summary, summary_paths = load_validation_data(
        search_root,
        include_non_ok=args.include_non_ok,
    )
    print(f"\nDiscovered {len(summary_paths)} validation_summary.json file(s):")
    for p in summary_paths:
        print(f"  {p.relative_to(search_root)}")
    print(f"\nLoaded {len(df)} row(s) for analysis.")
    print(f"  Noah: {len(df[df['system'] == 'noah'])}")
    print(f"  ElevenLabs: {len(df[df['system'] == 'elevenlabs'])}")
    print(f"  Runs: {', '.join(sorted(df['run_id'].unique()))}")
    print_non_ok_summary(
        non_ok_summary,
        included_in_analysis=args.include_non_ok,
    )

    print("\n" + "=" * 60)
    print("Phase 2: Descriptive statistics")
    print("=" * 60)
    desc = compute_descriptive_stats(df)

    print("\n" + "=" * 60)
    print("Phase 3: Paired tests (exact permutation + FDR)")
    print("=" * 60)
    test_results = run_paired_tests(df, alternative=alternative)
    desc_with_leads = merge_desc_with_rank_calls(desc, test_results)
    print_descriptive_table(desc_with_leads)
    print_test_table(test_results)

    print("\n" + "=" * 60)
    print("Phase 4: Verdict")
    print("=" * 60)
    verdict = build_verdict(test_results, alternative=alternative)
    print("\n" + verdict)

    output_path = args.output.resolve()
    write_markdown_report(
        output_path=output_path,
        summary_paths=summary_paths,
        search_root=search_root,
        df=df,
        non_ok_summary=non_ok_summary,
        include_non_ok=args.include_non_ok,
        desc_with_leads=desc_with_leads,
        test_results=test_results,
        verdict=verdict,
        alternative=alternative,
    )
    print(f"\nReport written to: {output_path}")


if __name__ == "__main__":
    main()
