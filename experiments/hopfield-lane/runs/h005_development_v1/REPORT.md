# H005: matched present expression and future continuation

PROSPECTIVE_FUTURES_ON_DEVELOPMENT_CHECKPOINTS. Decision: **DOES_NOT_QUALIFY**.
106/384 candidate pairs matched in 24/24 base networks. Eight future branches per pair; 16 additional replacements.
Inputs are exposed H003 development checkpoints; future tapes are new. Every candidate pair was simulated, including nonmatches. The independent unit is the base network.

| Packet history | Validation current success | Terminal renewed success | Uninterrupted success | Protected-copy terminal success |
|---|---:|---:|---:|---:|
| gain1_history | 96.53% [94.92, 97.88] | 83.46% [80.41, 86.46] | 69.00% [65.03, 72.98] | 96.13% [94.04, 97.87] |
| gain4_history | 98.11% [97.40, 98.79] | 87.49% [83.78, 90.97] | 75.44% [70.40, 80.25] | 97.90% [96.72, 98.95] |

## Decisions and controls

Failed gates: history_gain4_minus_gain1_minimum_effect.
Current-expression validation uses separate probes and 90% intervals contained within the prespecified five-point bounds for success and all four output means. These probes never change eligibility.
Primary future contrasts use one-sided Bonferroni percentile lower bounds at .05/5. Displayed intervals are marginal 95% whole-network bootstrap intervals. All mean-effect minima and coverage gates are required.

| Primary difference | Estimate [95% interval], percentage points | Adjusted lower, points |
|---|---:|---:|
| history_gain4_minus_gain1 | 4.03% [1.97, 6.18] | 1.59 |
| gain4_own_minus_foreign | 78.64% [73.72, 83.32] | 72.75 |
| gain4_own_minus_read_off | 87.49% [83.78, 90.97] | 83.05 |
| gain4_own_minus_write_off | 87.49% [83.78, 90.97] | 83.05 |
| gain4_own_minus_damaged_copy | 87.49% [83.78, 90.97] | 83.05 |

| Record arm | Gain-1-history terminal success | Gain-4-history terminal success |
|---|---:|---:|
| renewal | 83.46% [80.41, 86.46] | 87.49% [83.78, 90.97] |
| equalized | 87.49% [83.78, 90.97] | 87.49% [83.78, 90.97] |
| foreign | 32.98% [27.06, 39.15] | 8.85% [6.45, 11.34] |
| protected_copy | 96.13% [94.04, 97.87] | 97.90% [96.72, 98.95] |
| damaged_copy | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| read_off | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |
| write_off | 0.00% [0.00, 0.00] | 0.00% [0.00, 0.00] |

## Interpretation boundary

The future reader, writer, damage law and time budget are identical across histories. Equalized packets must yield identical future activity and records. Present matching concerns a finite output observer; it does not assert identical hidden states or exact latent readout probabilities.
Matching after different histories does not isolate the total or direct causal effect of past gain. Paired packet transplantation tests their consequences within the selected set. Full block counts, empty blocks, current validation intervals, and all candidate-pair outcomes are retained in summary.json and pair_summary.npz.
Failure of coverage, current validation or the primary cannot be replaced by a favorable all-candidate, intermediate-horizon or uninterrupted result. This study fits no predictor and establishes no unique theory. H004 confirmation remains unchanged.
Each packet still has 2016 independent symmetric entries, stored as float64 during dynamics. Exact ternary int8 archival coding saves disk space without changing the transmission boundary. Copying requires less computation than the diagnostic bodies simulated here. No private model, state or result enters this study.
Retained audit passed: True.
