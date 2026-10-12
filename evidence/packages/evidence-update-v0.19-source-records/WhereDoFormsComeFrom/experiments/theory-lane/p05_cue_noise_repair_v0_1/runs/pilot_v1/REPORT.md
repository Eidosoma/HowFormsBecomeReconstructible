# Repeated repair under cue noise mismatch

Under independent cue noise, repeated repair minus baseline uninterrupted success is +9.38 percentage points, with descriptive 95% stratified block-bootstrap interval [+6.25, +12.50]. The primary estimate and its descriptive interval are positive.

All 256 starting records were retained for generations 15 to 32. The primary endpoint requires every subsequent reconstruction to pass both cues. Teaching and resets remain matched. Only the correlation of ongoing noise between the two cue episodes changes; marginal variance is fixed. Injury and reset draws are shared across all arms, and noise is shared across the two repair policies within each regime.

| Cue noise | Baseline uninterrupted | Repeated repair uninterrupted | Baseline generation 32 | Repeated repair generation 32 |
|---|---:|---:|---:|---:|
| matched | 47.27% | 91.02% | 81.64% | 96.48% |
| noise_0999 | 70.31% | 91.02% | 90.62% | 94.53% |
| noise_0 | 82.03% | 91.41% | 90.23% | 94.14% |

| Contrast | Uninterrupted difference pp | Descriptive 95% interval pp | Positive tied negative blocks |
|---|---:|---:|---:|
| matched_repeated_minus_baseline | +43.75 | [+37.89, +49.61] | 16 / 0 / 0 |
| noise_0999_repeated_minus_baseline | +20.70 | [+15.62, +25.78] | 15 / 1 / 0 |
| noise_0_repeated_minus_baseline | +9.38 | [+6.25, +12.50] | 14 / 1 / 1 |
| noise_0999_repeated_minus_matched | +0.00 | [+0.00, +0.00] | 0 / 16 / 0 |
| noise_0_repeated_minus_matched | +0.39 | [-0.78, +1.56] | 2 / 13 / 1 |
| noise_0999_baseline_minus_matched | +23.05 | [+17.58, +28.52] | 14 / 2 / 0 |
| noise_0_baseline_minus_matched | +34.77 | [+29.69, +39.84] | 16 / 0 / 0 |
| noise_0999_gain_minus_matched | -23.05 | [-28.52, -17.58] | 0 / 2 / 14 |
| noise_0_gain_minus_matched | -34.38 | [-39.06, -29.30] | 0 / 0 / 16 |

Independent-noise paired uninterrupted outcomes: 25 repair-only successes, 1 baseline-only successes, 209 both, and 21 neither.

A shrinking repair advantage must be interpreted alongside absolute rates and each policy’s change from matched noise. Baseline improvement does not by itself show repair fragility. Descriptive contrasts do not establish equivalence or noninferiority. Secondary matched, slight-mismatch or terminal outcomes cannot rescue a failed primary forecast.

| Arm | Available fallback edges fraction | Returning fallback edges fraction | Repair calls | Added edge events |
|---|---:|---:|---:|---:|
| matched_baseline | 17.86% | 100.00% | 0 | 0 |
| matched_repeated | 0.01% | 0.01% | 4608 | 422120 |
| noise_0999_baseline | 0.00% | 0.00% | 0 | 0 |
| noise_0999_repeated | 0.00% | 0.00% | 4608 | 422120 |
| noise_0_baseline | 0.00% | 0.00% | 0 | 0 |
| noise_0_repeated | 0.00% | 0.00% | 4608 | 422120 |

Fallback counts describe exact-zero contrast in the original writer; they do not identify a causal share of repair benefit. Returning edges are currently available edges incident to a cell absent in the previous reconstruction. The initial prior injury is retained from generation 14.

| Noise regime | Measured correlation | Plus variance | Minus variance |
|---|---:|---:|---:|
| matched | 1.000000 | 1.000003 | 1.000003 |
| noise_0999 | 0.999000 | 1.000003 | 1.000003 |
| noise_0 | 0.000004 | 1.000003 | 0.999986 |

Noise diagnostics refer to standard-normal forcing before multiplication by .02. Shared founders and repair-policy copies are counted once per original noise family; Gaussian draw counts are not the statistical inference units.

The cohort and all matched-control trajectories were exposed before design. Both matched arms replayed the preceding experiment byte for byte through all 18 generations. Only the four mismatched arms contribute new continuation outcomes, generated after protocol freeze. This is a mechanism follow-up within one simulator, not a new-cohort validation or external replication.

All optimizer results, repair constructions, body captures, damage masks, noise moments, saved-window scores, historical matched controls and analysis summaries were checked internally. Separate flat dynamics checks cover all six arms for case 0 at generations 15 and 32 in every block. Blocks are the inference units; intervals are descriptive paired bootstraps stratified across the four starting histories.

Repair uses only its incoming record and the fixed solver options. Every branch writes its own successor. All records occupy 4096 bytes. Added edges, magnitudes, solver diagnostics and intervention CPU time are retained separately from audit costs. The apparatus, input ports, algorithm and resources remain supplied; no outcome uniquely confirms RDT or establishes autonomous maintenance.

Generation curves, recovery, opposite-task expression, history summaries and resource details are retained in analysis.json and the raw evidence. No automatic successor is launched.
