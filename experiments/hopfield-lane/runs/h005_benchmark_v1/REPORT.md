# H005: matched present expression and future continuation

ENGINEERING_BENCHMARK. Decision: **ENGINEERING_ONLY**.
2/16 candidate pairs matched in 1/1 base networks. Eight future branches per pair; 16 additional replacements.
Inputs are exposed H003 development checkpoints; future tapes are new. Every candidate pair was simulated, including nonmatches. The independent unit is the base network.

| Packet history | Validation current success | Terminal renewed success | Uninterrupted success | Protected-copy terminal success |
|---|---:|---:|---:|---:|
| gain1_history | 93.75% [no interval] | 75.00% [no interval] | 62.50% [no interval] | 100.00% [no interval] |
| gain4_history | 93.75% [no interval] | 75.00% [no interval] | 62.50% [no interval] | 100.00% [no interval] |

## Decisions and controls

Failed gates: at_least_64_matched_pairs, at_least_16_nonempty_blocks, current_success_equivalent_within_5pp, current_output_0_equivalent_within_5pp, current_output_1_equivalent_within_5pp, current_output_2_equivalent_within_5pp, current_output_3_equivalent_within_5pp, history_gain4_minus_gain1_minimum_effect, history_gain4_minus_gain1_positive_adjusted_lower, gain4_own_minus_foreign_positive_adjusted_lower, gain4_own_minus_read_off_positive_adjusted_lower, gain4_own_minus_write_off_positive_adjusted_lower, gain4_own_minus_damaged_copy_positive_adjusted_lower.
Current-expression validation uses separate probes and 90% intervals contained within the prespecified five-point bounds for success and all four output means. These probes never change eligibility.
Primary future contrasts use one-sided Bonferroni percentile lower bounds at .05/5. Displayed intervals are marginal 95% whole-network bootstrap intervals. All mean-effect minima and coverage gates are required.

| Primary difference | Estimate [95% interval], percentage points | Adjusted lower, points |
|---|---:|---:|
| history_gain4_minus_gain1 | 0.00% [no interval] | unavailable |
| gain4_own_minus_foreign | 62.50% [no interval] | unavailable |
| gain4_own_minus_read_off | 75.00% [no interval] | unavailable |
| gain4_own_minus_write_off | 75.00% [no interval] | unavailable |
| gain4_own_minus_damaged_copy | 75.00% [no interval] | unavailable |

| Record arm | Gain-1-history terminal success | Gain-4-history terminal success |
|---|---:|---:|
| renewal | 75.00% [no interval] | 75.00% [no interval] |
| equalized | 75.00% [no interval] | 75.00% [no interval] |
| foreign | 68.75% [no interval] | 12.50% [no interval] |
| protected_copy | 100.00% [no interval] | 100.00% [no interval] |
| damaged_copy | 0.00% [no interval] | 0.00% [no interval] |
| read_off | 0.00% [no interval] | 0.00% [no interval] |
| write_off | 0.00% [no interval] | 0.00% [no interval] |

## Interpretation boundary

The future reader, writer, damage law and time budget are identical across histories. Equalized packets must yield identical future activity and records. Present matching concerns a finite output observer; it does not assert identical hidden states or exact latent readout probabilities.
Matching after different histories does not isolate the total or direct causal effect of past gain. Paired packet transplantation tests their consequences within the selected set. Full block counts, empty blocks, current validation intervals, and all candidate-pair outcomes are retained in summary.json and pair_summary.npz.
Failure of coverage, current validation or the primary cannot be replaced by a favorable all-candidate, intermediate-horizon or uninterrupted result. This study fits no predictor and establishes no unique theory. H004 confirmation remains unchanged.
Each packet still has 2016 independent symmetric entries, stored as float64 during dynamics. Exact ternary int8 archival coding saves disk space without changing the transmission boundary. Copying requires less computation than the diagnostic bodies simulated here. No private model, state or result enters this study.
Retained audit passed: True.
