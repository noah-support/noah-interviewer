# UX survey statistics

Between-subjects analysis comparing two AI interview systems (Type A vs Type B) on Likert survey items. The pipeline is implemented in [`ux_survey_analysis.py`](ux_survey_analysis.py).

## Quick start

From the repository root:

```bash
python3 -m venv .venv-ux
source .venv-ux/bin/activate   # Windows: .venv-ux\Scripts\activate
pip install -r scripts/ux_survey_requirements.txt
python scripts/ux_survey_analysis.py
```

Optional arguments:

```bash
python scripts/ux_survey_analysis.py \
  --input /path/to/ux-test-results.csv \
  --output-dir /path/to/output/folder
```

Defaults:

- **Input:** `scripts/ux-test-results.csv`
- **Output:** `scripts/ux-test-results/output/`

The script prints a phase-by-phase log and ends with a short summary of significant (and non-significant) items.

## Input data

The exporter should produce a CSV (or XLSX) with:

- A **title row** on line 1 (skipped on load)
- **Headers** on line 2
- **Semicolon** (`;`) delimiter for CSV
- Grouping column: `Which AI interview system did you use?` with exactly two values (`Type A`, `Type B`)

Ten numeric Likert/rating columns are analysed; free-text and section-header columns are ignored except during load inspection. See `RENAME_MAP` in the script for the full question text → camelCase mapping.

If responses are stored as text (e.g. “Strongly agree”), the script maps them using an explicit ordinal dictionary and prints any values it cannot map.

## What the script does (phases)

| Phase | Function | Purpose |
|-------|----------|---------|
| 1 | `load_and_inspect` | Load data, print columns/dtypes, group counts, unique values and scale ranges per item |
| 1b | `apply_column_mapping` | Rename columns to camelCase; save `column_mapping.csv`; fail if any mapped column is missing |
| 1c | `verify_section_construct_mapping` | Print each construct with original question text (not survey Section N headers) |
| 2 | `clean_and_recode` | Map groups to `typeA` / `typeB`, coerce items to numeric, report missingness |
| 3 | `compute_descriptives` | Per item × group: n, mean, std, **median**, **IQR** |
| 4 | Mann-Whitney + Welch + Shapiro | Primary non-parametric tests; secondary t-tests; normality appendix |
| 5 | `apply_mcc` | Benjamini–Hochberg FDR and Holm–Bonferroni on 10 item p-values |
| 6 | `analyze_section_composites` | Cronbach’s α and Mann-Whitney on section mean scores |
| 7 | Plots + `print_summary` | Violin/box plots per item; console summary |

## Statistical approach

### Design

- **Between-subjects:** each participant used one system only.
- **Groups:** Type A → `typeA`, Type B → `typeB`.
- **Missing data:** pairwise deletion per item (a blank on one question does not drop the participant from other items).

### Primary test (per item)

**Mann-Whitney U** (two-sided, independent samples):

- Appropriate for comparing two independent groups on ordinal Likert ratings.
- Always uses scipy’s **asymptotic** method with **tie correction** and **continuity correction** (`method='asymptotic'`, `use_continuity=True`). The exact method is not used because clustered Likert responses (mostly 3–5) produce many ties, and the exact method does not correct for them.
- **Effect sizes:** rank-biserial correlation (RBC) from pingouin; also r = |Z| / √N from a normal approximation of U.
- **Direction:** which group has the higher **median** (`higherGroup`: `typeA`, `typeB`, or `tie`).

Use **medians and IQRs** as the primary descriptives when reporting non-parametric results.

### Secondary test (robustness only)

**Welch’s t-test** (unequal variances) and **Cohen’s d** — reported separately, not used to choose the primary test. Shapiro–Wilk per group per item is saved in `shapiro_appendix.csv` for transparency only.

### Multiple comparisons

Ten items are tested at once:

- **Primary adjustment:** Benjamini–Hochberg FDR (`p_fdr`), significance flag `sig_fdr` at α = 0.05.
- **Conservative alternative:** Holm–Bonferroni (`p_holm`, `sig_holm`).

Interpret item-level conclusions using **FDR-adjusted** p-values, not raw p-values.

### Section composites

Construct groupings come from the explicit `RENAME_MAP` / `SECTIONS` dict in code, not from the survey export’s “Section 2 / 3 / 4” header rows. After rename, the script prints each construct with its assigned question text so you can verify the mapping.

| Section | Items |
|---------|--------|
| `interactionQuality` | understoodResponses, relevantFollowUps, naturalConversation |
| `voiceDelivery` | voiceClarity, appropriateTone, comfortablePacing |
| `overallSection` | feltAtEase, technicalEaseOfUse, overallExperience, wouldUseAgain |

For each section:

1. **Zero-variance items** (e.g. every response = 5) are excluded from Cronbach’s α and from any composite, because they distort reliability.
2. **Cronbach’s α** is computed on the remaining items (complete cases only).
3. **Mann-Whitney U** on a section mean composite runs only when α ≥ 0.70. Sections below that threshold are reported with α and an explicit note to interpret items individually — no composite test.
4. With the current data, typically only `overallSection` is testable; low-α sections are documented in `cronbach_alpha.csv` and the summary.

Section results are supplementary; they do not replace per-item tests. A non-significant composite result does not imply equivalence given the small sample.

## Output files

All paths are relative to `--output-dir` (default: `ux-test-results/output/`).

| File | Contents |
|------|----------|
| `column_mapping.csv` | camelCase ↔ original survey question |
| `missingness.csv` | Missing and valid n per item per group |
| `descriptive_stats.csv` | n, mean, std, median, IQR, Q1, Q3 |
| `survey_test_results.csv` | Main table: descriptives, U, raw/FDR/Holm p, effect sizes, significance |
| `secondary_tests.csv` | Welch t, p, Cohen’s d per item |
| `shapiro_appendix.csv` | Shapiro–Wilk per item per group |
| `cronbach_alpha.csv` | Section internal consistency |
| `section_composite_results.csv` | Section-level Mann-Whitney results |
| `plots/{item}.png` | Violin + box plot per item (title = full question text) |

### Reading `survey_test_results.csv`

Key columns:

- `median_typeA`, `median_typeB`, `iqr_typeA`, `iqr_typeB` — report these first.
- `p_raw` — uncorrected Mann-Whitney p-value.
- `p_fdr` — Benjamini–Hochberg adjusted; use with `sig_fdr` for conclusions.
- `rankBiserial` — effect size for the primary test.
- `higherGroup` — direction of median difference.

Example interpretation: if `sig_fdr` is `False`, there is no statistically significant difference between systems for that item after correcting for ten comparisons, regardless of how small `p_raw` looks.

## Survey items (camelCase)

| camelCase | Section |
|-----------|---------|
| `understoodResponses` | Interaction quality |
| `relevantFollowUps` | Interaction quality |
| `naturalConversation` | Interaction quality |
| `voiceClarity` | Voice and delivery |
| `appropriateTone` | Voice and delivery |
| `comfortablePacing` | Voice and delivery |
| `feltAtEase` | Overall experience |
| `technicalEaseOfUse` | Overall experience |
| `overallExperience` | Overall experience |
| `wouldUseAgain` | Overall experience |

## Reproducibility

- `RANDOM_SEED = 42` is set at startup (plot point jitter and any resampling).
- Dependencies are pinned in [`ux_survey_requirements.txt`](ux_survey_requirements.txt): pandas, scipy, pingouin, matplotlib, openpyxl (for XLSX input).

## Limitations (current data)

With about 15 participants split across two groups, statistical power is limited. Non-significant FDR results may reflect ceiling effects (many ratings at 4–5) as much as true equivalence. Always report effect sizes (RBC) alongside p-values.

The script does not deduplicate rows, model covariates, or run Bayesian analyses. Add those steps separately if needed.

## Dependencies

```bash
pip install -r scripts/ux_survey_requirements.txt
```

Packages: **pandas** (data), **scipy** (Mann-Whitney, Welch, Shapiro), **pingouin** (effect sizes, FDR/Holm, Cronbach’s α), **matplotlib** (plots).
