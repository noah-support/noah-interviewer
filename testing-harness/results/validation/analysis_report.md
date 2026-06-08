# Interview Validation Comparison Report

Generated: 2026-06-07 19:44:06 UTC

## Data sources

Search root: `/Users/cesarvanleuffelen/Documents/Noah/Research/noah-interviewer`

- `testing-harness/results/validation/run_1/validation_summary.json`
- `testing-harness/results/validation/run_2/validation_summary.json`

## Sample

- Paired observations: 8 complete (run_id, persona) pairs per metric
- Total rows in analysis set: 16
- Runs: run_1, run_2
- Personas: A, B, C, D

## Non-ok rows (excluded from analysis)

No non-ok rows found.

## Descriptive statistics

Judge scores (1–5 ordinal): **median and IQR** per system. Embedding similarity (continuous): **mean ± std**. **Noah leads?** follows the oriented rank-biserial sign (rank-based); parenthetical notes flag where the median/mean impression differs due to ties or skew.

### Core metrics

| label | noah | elevenlabs | noah_leads_rank_based |
| --- | --- | --- | --- |
| Overall Embedding Similarity | 0.5725 ± 0.2432 (n=8) | 0.5434 ± 0.1647 (n=8) | yes |

| label | noah | elevenlabs | noah_leads_rank_based |
| --- | --- | --- | --- |
| Activity Coverage | median 3.0, IQR 2.0 (n=8) | median 2.0, IQR 0.2 (n=8) | yes |
| Control Flow & Handoff Fidelity | median 2.0, IQR 1.5 (n=8) | median 1.5, IQR 1.0 (n=8) | yes |
| Attribute Accuracy | median 2.0, IQR 1.5 (n=8) | median 2.0, IQR 0.2 (n=8) | yes (median differs due to ties/skew) |
| Exception & Edge Case Capture | median 4.0, IQR 3.0 (n=8) | median 3.0, IQR 1.2 (n=8) | yes |
| Faithfulness (No Hallucination) | median 2.0, IQR 1.2 (n=8) | median 2.0, IQR 0.0 (n=8) | tie |

### Error counts

| label | noah | elevenlabs | noah_leads_rank_based |
| --- | --- | --- | --- |
| Total Missed Items | median 2.0, IQR 2.8 (n=8) | median 3.0, IQR 8.5 (n=8) | yes |
| Total Extra / Hallucinated Items | median 1.5, IQR 4.5 (n=8) | median 2.0, IQR 1.0 (n=8) | no (median differs due to ties/skew) |

## Research question

Is the Noah interview system significantly better than the ElevenLabs interviewer?

## Paired tests (one-sided: Noah > ElevenLabs (pre-specified), α = 0.05)

Matched pairs: each (run_id, persona) contributes one Noah and one ElevenLabs score against the same ground truth. Primary p-value: **exact sign-flip permutation** (enumerates all 2^n sign patterns; no asymptotic approximation). Cross-check: exact Wilcoxon signed-rank (drops zero-difference pairs; see `n_wilcoxon`). Multiplicity: **Benjamini-Hochberg FDR** across eight metrics.

| label | n_pairs | n_wilcoxon | p_raw | p_wilcoxon | p_fdr | rank_biserial | noah_significantly_better_fdr |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Overall Embedding Similarity | 8 | 8 | 0.3438 | 0.3711 | 0.4583 | 0.1667 | No |
| Activity Coverage | 8 | 7 | 0.1562 | 0.1094 | 0.3000 | 0.5714 | No |
| Control Flow & Handoff Fidelity | 8 | 5 | 0.1250 | 0.0938 | 0.3000 | 0.7333 | No |
| Attribute Accuracy | 8 | 4 | 0.1875 | 0.1875 | 0.3000 | 0.7000 | No |
| Exception & Edge Case Capture | 8 | 6 | 0.0938 | 0.0781 | 0.3000 | 0.7143 | No |
| Faithfulness (No Hallucination) | 8 | 5 | 0.5938 | 0.5938 | 0.6786 | -0.0667 | No |
| Total Missed Items | 8 | 8 | 0.1289 | 0.1562 | 0.3000 | 0.4722 | No |
| Total Extra / Hallucinated Items | 8 | 7 | 0.8125 | 0.7656 | 0.8125 | -0.2500 | No |

## Verdict

**Research question:** Is the Noah interview system significantly better than the ElevenLabs interviewer?

**Answer:** No — after paired testing and Benjamini-Hochberg FDR correction, we cannot conclude that Noah is significantly better than ElevenLabs on any tested metric. This does **not** mean the systems are equivalent: with n=8 pairs the analysis is underpowered and 'not significant' means the test could not detect a difference, not that none exists.

Tests: paired exact sign-flip permutation on matched (run_id, persona) differences; one-sided (H₁: Noah > ElevenLabs); α = 0.05. Wilcoxon signed-rank (exact) p-values are reported for cross-check. Benjamini-Hochberg FDR is applied across all eight tested metrics (six core + two error counts), consistent with the UX survey pipeline.

The directional hypothesis (Noah > ElevenLabs) was pre-specified in the analysis plan before inspecting validation outcomes.

Effect sizes: matched-pairs rank-biserial correlation (r), oriented so positive means Noah better. Directional lead/no-lead groupings follow the sign of r, not the median.

Limitation (permutation granularity): with 8 pairs the one-sided exact permutation p-value has a floor of 1/256 (≈0.0039). Many ordinal judge-score paired differences are zero (e.g. Faithfulness, where ElevenLabs has zero IQR), so the number of distinguishable sign patterns is smaller still and achievable p-values are coarser. This granularity, not only the small sample, is part of why no metric reaches significance.

Limitation (Wilcoxon cross-check): the exact Wilcoxon signed-rank p-values drop zero-difference pairs, so the effective pair count is below 8 for several metrics (see n_wilcoxon in the test table). Wilcoxon is reported only as a cross-check, not the primary result.

Noah leads (rank-based) but not significantly on: Overall Embedding Similarity (p_raw=0.3438, r=0.167), Activity Coverage (p_raw=0.1562, r=0.571), Control Flow & Handoff Fidelity (p_raw=0.1250, r=0.733), Attribute Accuracy (p_raw=0.1875, r=0.700), Exception & Edge Case Capture (p_raw=0.0938, r=0.714), Total Missed Items (p_raw=0.1289, r=0.472).

Noah does not lead (rank-based), or is tied, on: Faithfulness (No Hallucination) (tie, p_raw=0.5938, r=-0.067), Total Extra / Hallucinated Items (p_raw=0.8125, r=-0.250).

## Discussion

### Transcript task alignment

The two systems are not conducting identical interviews against the same scoring rubric in the same way. Noah's transcript is structured process mapping (steps, tools, handoffs, exceptions), while the ElevenLabs transcript is a general work interview (time estimates, frustrations, ambitions). The validation pipeline measures **process-reconstruction fidelity**, so ElevenLabs is partly penalized for not attempting structured extraction.

That may be exactly the thesis point — a purpose-built interviewer beats a generic one — but readers should not over-read these numbers as pure "Noah model vs ElevenLabs model" platform quality. The comparison reflects **configuration-for-task** as much as underlying capability.

### Error-count trade-off

Paired testing on error counts surfaces an honest trade-off: Noah tends to **miss fewer** ground-truth items (rank-based lead on missed items) but is **worse on precision** (oriented rank-biserial negative on extra/hallucinated items, despite a lower median driven by skew). That pattern is practically meaningful even when judge scores are flat — it suggests Noah extracts more aggressively, which helps recall but hurts precision.
