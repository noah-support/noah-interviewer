from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pingouin as pg
import scipy.stats as stats
import seaborn as sns
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
ALPHA = 0.05
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "ux-test-results.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "ux-test-results" / "output"

RENAME_MAP = {
    "Which AI interview system did you use?": "system",
    "The AI understood my responses accurately.": "understoodResponses",
    "The AI asked relevant and logical follow-up questions.": "relevantFollowUps",
    "The conversation felt natural and easy to follow.": "naturalConversation",
    "The AI's voice was clear and easy to understand.": "voiceClarity",
    "The AI's tone felt appropriate for an interview setting.": "appropriateTone",
    "The pacing of the conversation felt comfortable.": "comfortablePacing",
    "I felt at ease during the interview.": "feltAtEase",
    "The interview system was easy to use technically (no major issues or confusion).": "technicalEaseOfUse",
    "How would you rate your overall experience with this AI interview system?": "overallExperience",
    "I would be comfortable using this type of AI interview system again.": "wouldUseAgain",
}

ITEMS = [
    "understoodResponses",
    "relevantFollowUps",
    "naturalConversation",
    "voiceClarity",
    "appropriateTone",
    "comfortablePacing",
    "feltAtEase",
    "technicalEaseOfUse",
    "overallExperience",
    "wouldUseAgain",
]

SECTIONS = {
    "interactionQuality": [
        "understoodResponses",
        "relevantFollowUps",
        "naturalConversation",
    ],
    "voiceDelivery": [
        "voiceClarity",
        "appropriateTone",
        "comfortablePacing",
    ],
    "overallSection": [
        "feltAtEase",
        "technicalEaseOfUse",
        "overallExperience",
        "wouldUseAgain",
    ],
}

SYSTEM_RAW_TO_LABEL = {
    "Type A": "typeA",
    "Type B": "typeB",
}

SYSTEM_LABEL_TO_DISPLAY = {
    "typeA": "Type A",
    "typeB": "Type B",
}

# Explicit ordinal text mapping (printed at runtime if used)
LIKERT_TEXT_MAP = {
    "strongly disagree": 1,
    "disagree": 2,
    "neutral": 3,
    "neither agree nor disagree": 3,
    "agree": 4,
    "strongly agree": 5,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
}

CRONBACH_ALPHA_THRESHOLD = 0.70
BOOTSTRAP_N_RESAMPLES = 5000
BOOTSTRAP_CONFIDENCE = 0.95

DIRECTION_LABELS = {
    "typeA": "Leans Type A",
    "typeB": "Leans Type B",
    "tie": "Neutral",
    "insufficient_data": "Insufficient data",
    "not_tested": "Not tested",
}
DIRECTION_PRINT_ORDER = ["typeA", "typeB", "tie", "insufficient_data"]

# Mann-Whitney U: asymptotic normal approximation with tie + continuity correction
# (required for clustered Likert responses; exact method does not correct for ties).
MWU_METHOD = "asymptotic"
MWU_USE_CONTINUITY = True
MWU_METHOD_LABEL = (
    "asymptotic normal approximation with tie and continuity correction "
    "(clustered Likert responses produce many ties)"
)


def _mann_whitney_u(a: np.ndarray, b: np.ndarray) -> stats.MannwhitneyuResult:
    """Mann-Whitney U via scipy asymptotic path (tie-corrected variance)."""
    return stats.mannwhitneyu(
        a,
        b,
        alternative="two-sided",
        method=MWU_METHOD,
        use_continuity=MWU_USE_CONTINUITY,
    )


def _zero_variance_items(df: pd.DataFrame, items: list[str]) -> list[str]:
    """Items with a single unique non-missing value (distort Cronbach alpha)."""
    return [item for item in items if df[item].dropna().nunique() <= 1]


def _read_data_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(
            path,
            skiprows=1,
            sep=";",
            encoding="utf-8",
            quotechar='"',
        )
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path, skiprows=1)
    raise ValueError(f"Unsupported file format: {suffix}")


def load_and_inspect(path: Path) -> pd.DataFrame:
    """Phase 1: Load data and print structure before rename."""
    print("=" * 60)
    print("Phase 1: Load and inspect")
    print("=" * 60)

    df = _read_data_file(path)
    print(f"\nFile: {path}")
    print(f"Rows: {len(df)}")
    print("\nColumn names and dtypes:")
    for col in df.columns:
        print(f"  {col!r}: {df[col].dtype}")

    group_col = "Which AI interview system did you use?"
    if group_col not in df.columns:
        raise KeyError(f"Missing grouping column: {group_col!r}")

    print(f"\nGrouping column {group_col!r}:")
    counts = df[group_col].astype(str).str.strip().value_counts()
    print(counts)
    n_groups = counts.shape[0]
    if n_groups != 2:
        raise ValueError(f"Expected exactly 2 groups, found {n_groups}: {counts.index.tolist()}")

    print("\nTarget items — unique raw values and inferred scale (pre-rename):")
    for orig_col, camel in RENAME_MAP.items():
        if orig_col == group_col:
            continue
        if orig_col not in df.columns:
            raise ValueError(
                f"Target survey column not found in file: {orig_col!r} (maps to {camel})"
            )
        raw = df[orig_col].dropna()
        uniques = sorted(raw.astype(str).str.strip().unique().tolist())
        numeric_preview = pd.to_numeric(raw, errors="coerce")
        n_num = numeric_preview.notna().sum()
        if n_num > 0:
            lo, hi = numeric_preview.min(), numeric_preview.max()
            scale_note = f"numeric preview range [{lo}, {hi}]"
        else:
            scale_note = "no numeric values after coercion"
        label = " (overall experience)" if camel == "overallExperience" else ""
        print(f"  {camel}{label}:")
        print(f"    unique raw ({len(uniques)}): {uniques}")
        print(f"    {scale_note}")

    return df


def apply_column_mapping(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Phase 1b: Rename to camelCase and build mapping table."""
    print("\n" + "=" * 60)
    print("Phase 1b: Column mapping")
    print("=" * 60)

    missing = [k for k in RENAME_MAP if k not in df.columns]
    if missing:
        raise ValueError(
            "Rename map references columns not found in the file "
            f"(check survey export / column names): {missing}"
        )

    df = df.rename(columns=RENAME_MAP)
    question_map = {v: k for k, v in RENAME_MAP.items() if v != "system"}
    mapping_df = pd.DataFrame(
        [{"camelCase": k, "originalQuestion": v} for k, v in question_map.items()]
    )
    print(f"Renamed {len(RENAME_MAP)} columns; kept {len(df.columns)} total columns.")
    return df, mapping_df


def verify_section_construct_mapping(question_map: dict[str, str]) -> None:
    """After rename: confirm each construct maps to the intended survey questions."""
    print("\n" + "=" * 60)
    print("Construct verification (explicit rename dict only; not survey Section N headers)")
    print("=" * 60)

    missing_items = [item for item in ITEMS if item not in question_map]
    if missing_items:
        raise ValueError(f"Target items missing from column mapping: {missing_items}")

    for construct, camel_items in SECTIONS.items():
        print(f"\n  {construct}:")
        for camel in camel_items:
            if camel not in question_map:
                raise ValueError(
                    f"Construct {construct!r} references {camel!r}, "
                    "which is not in the rename mapping"
                )
            print(f"    {camel}  <-  {question_map[camel]!r}")

    print(
        "\n  Note: survey export headers may read Section 2/3/4; grouping above uses "
        "question text from RENAME_MAP only."
    )


def _coerce_item(series: pd.Series, item: str) -> pd.Series:
    """Coerce one item to numeric with explicit text mapping."""
    out = pd.to_numeric(series, errors="coerce")
    mask = out.isna() & series.notna()
    if not mask.any():
        return out

    unmapped_records: list[tuple[int, str]] = []
    for idx in series.index[mask]:
        raw_val = series.loc[idx]
        if pd.isna(raw_val):
            continue
        text = str(raw_val).strip()
        key = text.lower()
        if key in LIKERT_TEXT_MAP:
            out.loc[idx] = LIKERT_TEXT_MAP[key]
        else:
            unmapped_records.append((idx, text))

    if unmapped_records:
        print(f"\n  UNMAPPED values for {item}:")
        for idx, text in unmapped_records:
            print(f"    row index {idx}: {text!r}")

    return out


def clean_and_recode(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Phase 2: Clean system labels and recode Likert items."""
    print("\n" + "=" * 60)
    print("Phase 2: Clean and recode")
    print("=" * 60)

    print("\nLIKERT_TEXT_MAP used for text responses:")
    for k, v in sorted(LIKERT_TEXT_MAP.items(), key=lambda x: x[1]):
        print(f"  {k!r} -> {v}")

    df = df.copy()
    df["system"] = df["system"].astype(str).str.strip()
    unknown_systems = set(df["system"]) - set(SYSTEM_RAW_TO_LABEL)
    if unknown_systems:
        raise ValueError(f"Unknown system values: {unknown_systems}")

    df["system"] = df["system"].map(SYSTEM_RAW_TO_LABEL)
    df["system"] = pd.Categorical(
        df["system"],
        categories=["typeA", "typeB"],
        ordered=True,
    )

    print("\nGroup sizes after recoding:")
    print(df["system"].value_counts().sort_index())

    for item in ITEMS:
        if item not in df.columns:
            raise KeyError(f"Missing item column: {item}")
        df[item] = _coerce_item(df[item], item)

    # Missingness per item per group
    rows = []
    effective_n: dict[str, dict[str, int]] = {}
    for item in ITEMS:
        effective_n[item] = {}
        for grp in ["typeA", "typeB"]:
            sub = df.loc[df["system"] == grp, item]
            n_valid = int(sub.notna().sum())
            n_missing = int(sub.isna().sum())
            effective_n[item][grp] = n_valid
            rows.append(
                {
                    "item": item,
                    "group": grp,
                    "n_missing": n_missing,
                    "n_valid": n_valid,
                }
            )

    missingness_df = pd.DataFrame(rows)
    print("\nMissing values per item per group:")
    print(missingness_df.to_string(index=False))

    return df, missingness_df


def compute_descriptives(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 3: Descriptive statistics per item per group."""
    print("\n" + "=" * 60)
    print("Phase 3: Descriptive statistics")
    print("=" * 60)

    rows = []
    for item in ITEMS:
        for grp in ["typeA", "typeB"]:
            vals = df.loc[df["system"] == grp, item].dropna()
            if len(vals) == 0:
                rows.append(
                    {
                        "item": item,
                        "group": grp,
                        "n": 0,
                        "mean": np.nan,
                        "std": np.nan,
                        "median": np.nan,
                        "iqr": np.nan,
                        "q1": np.nan,
                        "q3": np.nan,
                    }
                )
                continue
            q1 = vals.quantile(0.25)
            q3 = vals.quantile(0.75)
            rows.append(
                {
                    "item": item,
                    "group": grp,
                    "n": len(vals),
                    "mean": vals.mean(),
                    "std": vals.std(ddof=1) if len(vals) > 1 else 0.0,
                    "median": vals.median(),
                    "iqr": q3 - q1,
                    "q1": q1,
                    "q3": q3,
                }
            )

    desc = pd.DataFrame(rows)
    print(desc.to_string(index=False))
    return desc


def _mann_whitney_z_from_u(u_stat: float, n1: int, n2: int) -> float:
    """Normal approximation z for Mann-Whitney U (two-sided)."""
    n1, n2 = float(n1), float(n2)
    mu = n1 * n2 / 2.0
    sigma = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    if sigma == 0:
        return 0.0
    return (u_stat - mu) / sigma


def _split_groups(df: pd.DataFrame, item: str) -> tuple[np.ndarray, np.ndarray]:
    a = df.loc[df["system"] == "typeA", item].dropna().to_numpy(dtype=float)
    b = df.loc[df["system"] == "typeB", item].dropna().to_numpy(dtype=float)
    return a, b


def _higher_group_effect(rbc: float) -> str:
    """Direction of effect from rank-biserial correlation (positive = typeA higher)."""
    if np.isnan(rbc):
        return "insufficient_data"
    if rbc > 0:
        return "typeA"
    if rbc < 0:
        return "typeB"
    return "tie"


def _rank_biserial_mwu(a: np.ndarray, b: np.ndarray) -> float:
    """Rank-biserial correlation from Mann-Whitney U (group A vs group B)."""
    if len(a) == 0 or len(b) == 0:
        return np.nan
    return float(pg.mwu(a, b, alternative="two-sided").squeeze()["RBC"])


def bootstrap_rbc_ci(
    a: np.ndarray,
    b: np.ndarray,
    *,
    n_resamples: int = BOOTSTRAP_N_RESAMPLES,
    confidence_level: float = BOOTSTRAP_CONFIDENCE,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    """95% percentile bootstrap CI for independent-samples rank-biserial correlation."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 1 or len(b) < 1:
        return np.nan, np.nan

    boot_rng = rng or np.random.default_rng(RANDOM_SEED)
    n_a, n_b = len(a), len(b)
    boot_stats = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        boot_a = a[boot_rng.integers(0, n_a, size=n_a)]
        boot_b = b[boot_rng.integers(0, n_b, size=n_b)]
        boot_stats[i] = _rank_biserial_mwu(boot_a, boot_b)

    alpha = 1.0 - confidence_level
    lo, hi = np.nanpercentile(boot_stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def _format_rbc_with_ci(
    rbc: float,
    ci_lower: float,
    ci_upper: float,
) -> str:
    if np.isnan(rbc):
        return "RBC: n/a"
    if np.isnan(ci_lower) or np.isnan(ci_upper):
        return f"RBC={rbc:.3f}"
    return f"RBC={rbc:.3f}, 95% CI [{ci_lower:.3f}, {ci_upper:.3f}]"


def _format_p_values(p_raw: float, p_fdr: float) -> str:
    raw_str = f"{p_raw:.4f}" if not np.isnan(p_raw) else "n/a"
    fdr_str = f"{p_fdr:.4f}" if not np.isnan(p_fdr) else "n/a"
    return f"(p_raw={raw_str}, p_fdr={fdr_str})"


def run_mann_whitney_battery(
    df: pd.DataFrame,
    items: list[str],
    question_map: dict[str, str],
) -> pd.DataFrame:
    """Phase 4 primary: Mann-Whitney U per item."""
    print("\n" + "=" * 60)
    print("Phase 4 (primary): Mann-Whitney U tests")
    print(f"  Method: {MWU_METHOD_LABEL}")
    print("=" * 60)

    rows = []
    for item in items:
        a, b = _split_groups(df, item)
        n_a, n_b = len(a), len(b)

        if n_a == 0 or n_b == 0:
            rows.append(
                {
                    "camelCase": item,
                    "questionText": question_map.get(item, item),
                    "n_typeA": n_a,
                    "n_typeB": n_b,
                    "U": np.nan,
                    "p_raw": np.nan,
                    "rankBiserial": np.nan,
                    "rbc_ci_lower": np.nan,
                    "rbc_ci_upper": np.nan,
                    "r_from_z": np.nan,
                    "higherGroup": "insufficient_data",
                }
            )
            continue

        u_res = _mann_whitney_u(a, b)

        rbc = _rank_biserial_mwu(a, b)
        rbc_ci_lower, rbc_ci_upper = bootstrap_rbc_ci(a, b)
        u_stat = float(u_res.statistic)

        # r = |Z| / sqrt(N) using normal approximation for U
        z = _mann_whitney_z_from_u(u_stat, n_a, n_b)
        n_total = n_a + n_b
        r_from_z = abs(z) / np.sqrt(n_total) if n_total > 0 else np.nan

        rows.append(
            {
                "camelCase": item,
                "questionText": question_map.get(item, item),
                "n_typeA": n_a,
                "n_typeB": n_b,
                "U": float(u_res.statistic),
                "p_raw": float(u_res.pvalue),
                "rankBiserial": rbc,
                "rbc_ci_lower": rbc_ci_lower,
                "rbc_ci_upper": rbc_ci_upper,
                "r_from_z": r_from_z,
                "higherGroup": _higher_group_effect(rbc),
            }
        )
        print(
            f"  {item}: {_format_rbc_with_ci(rbc, rbc_ci_lower, rbc_ci_upper)}, "
            f"U={u_res.statistic:.4g}, p={u_res.pvalue:.4g}, "
            f"higher={rows[-1]['higherGroup']}"
        )

    return pd.DataFrame(rows)


def run_shapiro_appendix(df: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    """Shapiro-Wilk per group per item (appendix only)."""
    rows = []
    for item in items:
        for grp in ["typeA", "typeB"]:
            vals = df.loc[df["system"] == grp, item].dropna().to_numpy(dtype=float)
            n = len(vals)
            if n < 3:
                rows.append(
                    {
                        "item": item,
                        "group": grp,
                        "n": n,
                        "W": np.nan,
                        "p_shapiro": np.nan,
                        "note": "n < 3",
                    }
                )
            elif n > 5000:
                rows.append(
                    {
                        "item": item,
                        "group": grp,
                        "n": n,
                        "W": np.nan,
                        "p_shapiro": np.nan,
                        "note": "n > 5000",
                    }
                )
            elif np.var(vals) == 0 or len(np.unique(vals)) == 1:
                rows.append(
                    {
                        "item": item,
                        "group": grp,
                        "n": n,
                        "W": np.nan,
                        "p_shapiro": np.nan,
                        "note": "zero variance",
                    }
                )
            else:
                w, p = stats.shapiro(vals)
                rows.append(
                    {
                        "item": item,
                        "group": grp,
                        "n": n,
                        "W": float(w),
                        "p_shapiro": float(p),
                        "note": "",
                    }
                )
    return pd.DataFrame(rows)


def apply_mcc(results: pd.DataFrame) -> pd.DataFrame:
    """Phase 5: Benjamini-Hochberg FDR and Holm-Bonferroni."""
    print("\n" + "=" * 60)
    print("Phase 5: Multiple comparison correction")
    print("=" * 60)

    out = results.copy()
    pvals = out["p_raw"].to_numpy(dtype=float)
    valid = ~np.isnan(pvals)

    out["p_fdr"] = np.nan
    out["p_holm"] = np.nan
    out["sig_fdr"] = False
    out["sig_holm"] = False

    if valid.sum() > 0:
        _, p_fdr = pg.multicomp(pvals[valid], method="fdr_bh")
        _, p_holm = pg.multicomp(pvals[valid], method="holm")
        out.loc[valid, "p_fdr"] = p_fdr
        out.loc[valid, "p_holm"] = p_holm
        out.loc[valid, "sig_fdr"] = p_fdr < ALPHA
        out.loc[valid, "sig_holm"] = p_holm < ALPHA

    print(out[["camelCase", "p_raw", "p_fdr", "p_holm", "sig_fdr"]].to_string(index=False))
    return out


def _merge_descriptives_into_results(
    results: pd.DataFrame, desc: pd.DataFrame
) -> pd.DataFrame:
    for grp, prefix in [("typeA", "typeA"), ("typeB", "typeB")]:
        sub = desc[desc["group"] == grp].set_index("item")
        results[f"median_{prefix}"] = results["camelCase"].map(sub["median"])
        results[f"iqr_{prefix}"] = results["camelCase"].map(sub["iqr"])
        results[f"mean_{prefix}"] = results["camelCase"].map(sub["mean"])
    return results


def analyze_section_composites(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Phase 6: Cronbach's alpha; Mann-Whitney only when alpha >= threshold."""
    print("\n" + "=" * 60)
    print("Phase 6: Section composite scores")
    print(f"  Composite Mann-Whitney only when Cronbach alpha >= {CRONBACH_ALPHA_THRESHOLD}")
    print(f"  Mann-Whitney method: {MWU_METHOD_LABEL}")
    print("=" * 60)

    alpha_rows = []
    composite_rows = []

    for section_name, items in SECTIONS.items():
        excluded = _zero_variance_items(df, items)
        alpha_items = [item for item in items if item not in excluded]

        if excluded:
            print(
                f"\n  {section_name}: excluding zero-variance item(s) from alpha/composite: "
                f"{excluded}"
            )

        section_df = df[alpha_items + ["system"]].dropna(subset=alpha_items, how="any")
        n_complete = len(section_df)

        alpha = np.nan
        alpha_ok = False
        if len(alpha_items) < 2:
            note = (
                "Fewer than two variable items after excluding zero-variance columns; "
                "interpret items individually."
            )
            print(f"  {section_name}: {note}")
        elif n_complete < 2:
            note = f"Insufficient complete cases (n={n_complete}); interpret items individually."
            print(f"  {section_name}: {note}")
        else:
            alpha, _ = pg.cronbach_alpha(data=section_df[alpha_items])
            alpha = float(alpha)
            alpha_ok = alpha >= CRONBACH_ALPHA_THRESHOLD
            status = "acceptable" if alpha_ok else "below threshold"
            print(
                f"  {section_name}: Cronbach alpha={alpha:.3f} ({status}), "
                f"n_complete={n_complete}, items_for_alpha={alpha_items}"
            )
            if not alpha_ok:
                note = (
                    f"Cronbach alpha={alpha:.3f} < {CRONBACH_ALPHA_THRESHOLD}; "
                    "section lacks internal consistency — interpret items individually, "
                    "not as a combined score."
                )
                print(f"    -> {note}")
            else:
                note = ""

        alpha_rows.append(
            {
                "section": section_name,
                "n_items_nominal": len(items),
                "items_nominal": ";".join(items),
                "excluded_zero_variance": ";".join(excluded) if excluded else "",
                "items_for_alpha": ";".join(alpha_items),
                "n_complete_cases": n_complete,
                "cronbach_alpha": alpha,
                "alpha_acceptable": alpha_ok if not np.isnan(alpha) else False,
                "composite_tested": alpha_ok and len(alpha_items) >= 2 and n_complete >= 2,
                "note": note if not alpha_ok else (
                    f"Excluded zero-variance: {', '.join(excluded)}" if excluded else ""
                ),
            }
        )

        if not alpha_ok or len(alpha_items) < 2 or n_complete < 2:
            composite_rows.append(
                {
                    "section": section_name,
                    "composite_tested": False,
                    "n_typeA": np.nan,
                    "n_typeB": np.nan,
                    "median_typeA": np.nan,
                    "median_typeB": np.nan,
                    "U": np.nan,
                    "p_raw": np.nan,
                    "rankBiserial": np.nan,
                    "rbc_ci_lower": np.nan,
                    "rbc_ci_upper": np.nan,
                    "higherGroup": "not_tested",
                    "test_method": "",
                    "note": alpha_rows[-1]["note"]
                    or "Composite not tested (reliability threshold not met).",
                }
            )
            continue

        composite_col = f"composite_{section_name}"
        df_work = df.copy()
        df_work[composite_col] = df_work[alpha_items].mean(axis=1, skipna=False)

        a, b = _split_groups(df_work, composite_col)
        n_a, n_b = len(a), len(b)

        if n_a == 0 or n_b == 0:
            composite_rows.append(
                {
                    "section": section_name,
                    "composite_tested": False,
                    "n_typeA": n_a,
                    "n_typeB": n_b,
                    "median_typeA": np.nan,
                    "median_typeB": np.nan,
                    "U": np.nan,
                    "p_raw": np.nan,
                    "rankBiserial": np.nan,
                    "rbc_ci_lower": np.nan,
                    "rbc_ci_upper": np.nan,
                    "higherGroup": "insufficient_data",
                    "test_method": MWU_METHOD,
                    "note": "Insufficient data per group for Mann-Whitney U.",
                }
            )
            continue

        u_res = _mann_whitney_u(a, b)
        rbc = _rank_biserial_mwu(a, b)
        rbc_ci_lower, rbc_ci_upper = bootstrap_rbc_ci(a, b)

        composite_rows.append(
            {
                "section": section_name,
                "composite_tested": True,
                "n_typeA": n_a,
                "n_typeB": n_b,
                "median_typeA": float(np.median(a)),
                "median_typeB": float(np.median(b)),
                "U": float(u_res.statistic),
                "p_raw": float(u_res.pvalue),
                "rankBiserial": rbc,
                "rbc_ci_lower": rbc_ci_lower,
                "rbc_ci_upper": rbc_ci_upper,
                "higherGroup": _higher_group_effect(rbc),
                "test_method": MWU_METHOD,
                "note": "",
            }
        )
        print(
            f"    Mann-Whitney on composite: {_format_rbc_with_ci(rbc, rbc_ci_lower, rbc_ci_upper)}, "
            f"U={u_res.statistic:.4g}, p={u_res.pvalue:.4g}, "
            f"higher={composite_rows[-1]['higherGroup']}"
        )

    comp_df = pd.DataFrame(composite_rows)
    return pd.DataFrame(alpha_rows), comp_df


def plot_items(
    df: pd.DataFrame,
    items: list[str],
    question_map: dict[str, str],
    out_dir: Path,
) -> None:
    """Box + strip plots per item (every response visible; no KDE)."""
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    plot_df = df[["system"] + items].copy()
    plot_df["system"] = plot_df["system"].map(SYSTEM_LABEL_TO_DISPLAY)

    for item in items:
        sub = plot_df[["system", item]].dropna()
        if sub.empty:
            continue

        y_min = int(np.floor(sub[item].min()))
        y_max = int(np.ceil(sub[item].max()))
        y_ticks = list(range(y_min, y_max + 1))

        fig, ax = plt.subplots(figsize=(8, 5))
        groups = ["Type A", "Type B"]

        sns.boxplot(
            data=sub,
            x="system",
            y=item,
            order=groups,
            ax=ax,
            width=0.45,
            showfliers=False,
            boxprops={"facecolor": "lightgray", "alpha": 0.35},
            medianprops={"color": "black", "linewidth": 2},
            zorder=1,
        )
        sns.stripplot(
            data=sub,
            x="system",
            y=item,
            order=groups,
            color="0.25",
            size=8,
            jitter=0.12,
            alpha=0.85,
            ax=ax,
            zorder=2,
        )

        ax.set_xlabel("")
        ax.set_yticks(y_ticks)
        ax.set_ylabel("Score")
        ax.set_title(question_map.get(item, item), fontsize=10, wrap=True)
        ax.set_ylim(y_min - 0.5, y_max + 0.5)
        ax.grid(axis="y", alpha=0.3)

        fig.tight_layout()
        out_path = plots_dir / f"{item}.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved plot: {out_path}")


def _print_item_result(row: pd.Series) -> None:
    med_a = row["median_typeA"]
    med_b = row["median_typeB"]
    med_a_str = f"{med_a:.2f}" if not np.isnan(med_a) else "n/a"
    med_b_str = f"{med_b:.2f}" if not np.isnan(med_b) else "n/a"
    rbc_line = _format_rbc_with_ci(
        row["rankBiserial"],
        row["rbc_ci_lower"],
        row["rbc_ci_upper"],
    )
    print(f"  - {row['camelCase']}")
    print(f"      Medians: Type A={med_a_str}, Type B={med_b_str}")
    print(f"      {rbc_line}")
    print(f"      {_format_p_values(row['p_raw'], row['p_fdr'])}")


def _print_composite_result(comp: pd.Series) -> None:
    rbc_line = _format_rbc_with_ci(
        comp["rankBiserial"],
        comp["rbc_ci_lower"],
        comp["rbc_ci_upper"],
    )
    print(
        f"      Medians: Type A={comp['median_typeA']:.2f}, "
        f"Type B={comp['median_typeB']:.2f}"
    )
    print(f"      {rbc_line}")
    print(f"      (p_raw={comp['p_raw']:.4g})")


def print_summary(
    df: pd.DataFrame,
    results: pd.DataFrame,
    section_results: pd.DataFrame,
    alpha_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Phase 7: Printed summary (effect-size first; underpowered n=15)."""
    print("\n" + "=" * 60)
    print("=== UX survey analysis summary ===")
    print("=" * 60)

    n_a = (df["system"] == "typeA").sum()
    n_b = (df["system"] == "typeB").sum()
    print(f"Participants: typeA (n={n_a}), typeB (n={n_b})")
    print(
        "Primary test: Mann-Whitney U (two-sided), "
        f"{MWU_METHOD_LABEL}"
    )
    print(
        "Interpretation: with n=15, emphasize effect direction and "
        "rank-biserial correlation (RBC) with 95% bootstrap CIs; "
        "p-values (incl. FDR) are secondary."
    )

    print("\nItem results grouped by direction of effect (RBC sign):")
    for direction_key in DIRECTION_PRINT_ORDER:
        label = DIRECTION_LABELS[direction_key]
        subset = results[results["higherGroup"] == direction_key]
        print(f"\n  {label} ({len(subset)} item(s)):")
        if len(subset) == 0:
            print("    (none)")
            continue
        for _, row in subset.iterrows():
            _print_item_result(row)

    print("\nSection composites (Cronbach alpha >= 0.70 required for testing):")
    for _, row in alpha_df.iterrows():
        section = row["section"]
        alpha = row["cronbach_alpha"]
        alpha_str = f"{alpha:.3f}" if not np.isnan(alpha) else "n/a"
        if row["composite_tested"]:
            comp = section_results[section_results["section"] == section].iloc[0]
            direction = DIRECTION_LABELS.get(comp["higherGroup"], comp["higherGroup"])
            print(f"  - {section}: TESTED (alpha={alpha_str}), {direction}")
            _print_composite_result(comp)
        else:
            note = row.get("note", "") or "Composite not tested."
            print(f"  - {section}: NOT TESTED (alpha={alpha_str}) — {note}")

    tested = section_results[section_results["composite_tested"] == True]  # noqa: E712
    if len(tested) > 0:
        print(
            "\n  Note: With n=15 split across two groups, wide bootstrap CIs and "
            "non-significant p-values cannot be taken as evidence of equivalence."
        )

    print(f"\nOutputs written to: {output_dir.resolve()}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="UX survey between-subjects analysis")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    np.random.seed(RANDOM_SEED)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1
    df_raw = load_and_inspect(args.input)

    # Phase 1b
    df, mapping_df = apply_column_mapping(df_raw)
    mapping_df.to_csv(output_dir / "column_mapping.csv", index=False)

    question_map = {
        row["camelCase"]: row["originalQuestion"]
        for _, row in mapping_df.iterrows()
    }
    verify_section_construct_mapping(question_map)

    print("\nPost-rename inspection for target items:")
    for item in ITEMS:
        raw = df[item].dropna()
        uniques = sorted(raw.astype(str).str.strip().unique().tolist())
        numeric = pd.to_numeric(raw, errors="coerce")
        if numeric.notna().any():
            lo, hi = numeric.min(), numeric.max()
            extra = f"range [{lo}, {hi}]"
        else:
            extra = "no numeric values"
        if item == "overallExperience":
            print(f"  {item} (overall experience): uniques={uniques}; {extra}")
        else:
            print(f"  {item}: uniques={uniques}; {extra}")

    # Phase 2
    df, missingness_df = clean_and_recode(df)
    missingness_df.to_csv(output_dir / "missingness.csv", index=False)

    # Phase 3
    desc = compute_descriptives(df)
    desc.to_csv(output_dir / "descriptive_stats.csv", index=False)

    # Phase 4
    mwu_results = run_mann_whitney_battery(df, ITEMS, question_map)
    shapiro_df = run_shapiro_appendix(df, ITEMS)
    shapiro_df.to_csv(output_dir / "shapiro_appendix.csv", index=False)

    results = apply_mcc(mwu_results)
    results = _merge_descriptives_into_results(results, desc)

    # Column order for final table
    col_order = [
        "camelCase",
        "questionText",
        "median_typeA",
        "median_typeB",
        "iqr_typeA",
        "iqr_typeB",
        "mean_typeA",
        "mean_typeB",
        "n_typeA",
        "n_typeB",
        "U",
        "rankBiserial",
        "rbc_ci_lower",
        "rbc_ci_upper",
        "higherGroup",
        "p_raw",
        "p_fdr",
        "p_holm",
        "sig_fdr",
        "sig_holm",
        "r_from_z",
    ]
    results = results[[c for c in col_order if c in results.columns]]
    results.to_csv(output_dir / "survey_test_results.csv", index=False)

    # Phase 6
    alpha_df, section_results = analyze_section_composites(df)
    alpha_df.to_csv(output_dir / "cronbach_alpha.csv", index=False)
    section_results.to_csv(output_dir / "section_composite_results.csv", index=False)

    # Phase 7 plots
    print("\n" + "=" * 60)
    print("Phase 7: Plots")
    print("=" * 60)
    plot_items(df, ITEMS, question_map, output_dir)

    print_summary(df, results, section_results, alpha_df, output_dir)


if __name__ == "__main__":
    main()
