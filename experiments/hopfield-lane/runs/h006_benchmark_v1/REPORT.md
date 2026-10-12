# H006: record organization at matched present function

ENGINEERING_BENCHMARK.

Dose selection uses eight exposed development networks; sixteen separate development networks test the selected dose. All H006 probes and future tapes are new. Present equivalence uses one-point bounds.

| Unique edge flips | Matched packets | Nonempty selection blocks | All current selection gates pass |
|---|---:|---:|---|
| 4 | 12 | 1 | False |
| 8 | 11 | 1 | False |
| 16 | 10 | 1 | False |
| 24 | 7 | 1 | False |
| 32 | 7 | 1 | False |

Selected dose: **32**.

Engineering assay matches: 8/16.

| Variant | Independent current success, % [95% interval] |
|---|---:|
| unchanged | 98.05 |
| output_flips | 95.12 |
| hidden_flips | 94.34 |

Failed current assay gates: at_least_64_matches, enough_nonempty_blocks, hidden_flips_current_success_at_least_95pct, unchanged_minus_output_flips_success_equivalent_within_1pp, unchanged_minus_output_flips_output_0_equivalent_within_1pp, unchanged_minus_output_flips_output_1_equivalent_within_1pp, unchanged_minus_output_flips_output_2_equivalent_within_1pp, unchanged_minus_output_flips_output_3_equivalent_within_1pp, unchanged_minus_hidden_flips_success_equivalent_within_1pp, unchanged_minus_hidden_flips_output_0_equivalent_within_1pp, unchanged_minus_hidden_flips_output_1_equivalent_within_1pp, unchanged_minus_hidden_flips_output_2_equivalent_within_1pp, unchanged_minus_hidden_flips_output_3_equivalent_within_1pp, hidden_flips_minus_output_flips_success_equivalent_within_1pp, hidden_flips_minus_output_flips_output_0_equivalent_within_1pp, hidden_flips_minus_output_flips_output_1_equivalent_within_1pp, hidden_flips_minus_output_flips_output_2_equivalent_within_1pp, hidden_flips_minus_output_flips_output_3_equivalent_within_1pp.

| Variant | Terminal renewal, % [95% interval] | Uninterrupted, % | Protected copy, % |
|---|---:|---:|---:|
| unchanged | 95.31 | 93.75 | 98.44 |
| output_flips | 95.31 | 93.75 | 96.88 |
| hidden_flips | 93.75 | 90.62 | 95.31 |

| Primary contrast | Difference, percentage points [95% interval] | Adjusted lower, points |
|---|---:|---:|
| unchanged_minus_output_flips | 0.00 | unavailable |
| hidden_flips_minus_output_flips | -1.56 | unavailable |
| unchanged_minus_foreign | 89.06 | unavailable |
| unchanged_minus_read_off | 95.31 | unavailable |
| unchanged_minus_write_off | 95.31 | unavailable |
| unchanged_minus_damaged_copy | 95.31 | unavailable |

Failed future decision gates: current_passed, unchanged_minus_output_flips_minimum_effect, unchanged_minus_output_flips_positive_adjusted_lower, hidden_flips_minus_output_flips_minimum_effect, hidden_flips_minus_output_flips_positive_adjusted_lower, unchanged_minus_foreign_positive_adjusted_lower, unchanged_minus_read_off_positive_adjusted_lower, unchanged_minus_write_off_positive_adjusted_lower, unchanged_minus_damaged_copy_positive_adjusted_lower.

| Record arm | Unchanged, % | Output flips, % | Hidden flips, % |
|---|---:|---:|---:|
| renewal | 95.31 | 95.31 | 93.75 |
| restored | 95.31 | 95.31 | 95.31 |
| foreign | 6.25 | 9.38 | 10.94 |
| protected_copy | 98.44 | 96.88 | 95.31 |
| damaged_copy | 0.00 | 0.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 |

**Decision: ENGINEERING_ONLY.**

Each intervention preserves the record histogram, norm and nonzero count. The locations have matched cue degrees and equal gained perturbation strength. Hidden connections are an active comparator. Base-plus-record norm is retained separately because its cross terms may differ.
Current validation concerns a finite observer, not exact latent current equality. Present-based selection limits the estimand to the declared matched packets. All decisions and current intervals, including failed doses, are retained in summary.json. No smaller effect, different dose, all-candidate subset, intermediate checkpoint or uninterrupted outcome can replace a failed primary.
The records are intervened on at the initial boundary; all later renewal writes use only current body activity. This study does not establish discovered competence or superiority to copying. No private material is imported; H004/H005 and the forms manuscript are unchanged.
Retained audit passed: True.
