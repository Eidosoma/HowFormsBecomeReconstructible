# H008: durability after a coherent hidden-pattern intervention

ENGINEERING_BENCHMARK.

**Decision: ENGINEERING_ONLY.**

Fixed dose: 8 hidden pairs. Fixed H007 membership: 14 packets across 1 networks. The original pre-replacement packets start new lineages; H007 survivors and outgoing packets do not select or initialize them.

| Variant | Fresh current success, % [95% interval] |
|---|---:|
| unchanged | 97.21 |
| hidden_swap | 96.76 |

| Current difference, swapped minus unchanged | Mean, points | 97.5% equivalence interval, points |
|---|---:|---:|
| success | -0.45 | [unavailable, unavailable] |
| output_0 | -0.67 | [unavailable, unavailable] |
| output_1 | -0.67 | [unavailable, unavailable] |
| output_2 | -0.22 | [unavailable, unavailable] |
| output_3 | -0.22 | [unavailable, unavailable] |

Failed current gates: at_least_64_matches, at_least_16_networks, success_equivalent_within_1pp, output_0_equivalent_within_1pp, output_1_equivalent_within_1pp, output_2_equivalent_within_1pp, output_3_equivalent_within_1pp.

## Prespecified terminal test

Primary: **swapped minus unchanged renewal success after sixteen replacements**. The two-sided question was declared before H008 outcomes. Absolute mean difference must reach ten percentage points and the adjusted interval must exclude zero.

Observed difference: **-1.79 percentage points**. Adjusted two-sided interval: **[unavailable, unavailable] points**.

| Arm | Unchanged terminal success, % [95% interval] | Swapped terminal success, % [95% interval] |
|---|---:|---:|
| renewal | 93.75 | 91.96 |
| restored | 93.75 | 93.75 |
| foreign | 8.04 | 8.04 |
| protected_copy | 99.11 | 98.21 |
| damaged_copy | 0.00 | 0.00 |
| read_off | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 |

| Route contrast | Difference, points [95% interval] | Adjusted lower, points |
|---|---:|---:|
| unchanged_renewal_minus_foreign | 85.71 | unavailable |
| unchanged_renewal_minus_read_off | 93.75 | unavailable |
| unchanged_renewal_minus_write_off | 93.75 | unavailable |
| unchanged_renewal_minus_damaged_copy | 93.75 | unavailable |
| hidden_swap_renewal_minus_foreign | 83.93 | unavailable |
| hidden_swap_renewal_minus_read_off | 91.96 | unavailable |
| hidden_swap_renewal_minus_write_off | 91.96 | unavailable |
| hidden_swap_renewal_minus_damaged_copy | 91.96 | unavailable |

Each variant must beat foreign, read-off, write-off and damaged copying by at least 15 points with positive adjusted lower bounds. The nine-test family uses .05/9 per test: two primary tails of .05/18 and one-sided control bounds at .05/9. Other displayed intervals are marginal 95%.

Failed qualification gates: current_passed, absolute_terminal_difference_at_least_10pp, adjusted_primary_interval_excludes_zero, unchanged_renewal_minus_foreign_positive_adjusted_lower, unchanged_renewal_minus_read_off_positive_adjusted_lower, unchanged_renewal_minus_write_off_positive_adjusted_lower, unchanged_renewal_minus_damaged_copy_positive_adjusted_lower, hidden_swap_renewal_minus_foreign_positive_adjusted_lower, hidden_swap_renewal_minus_read_off_positive_adjusted_lower, hidden_swap_renewal_minus_write_off_positive_adjusted_lower, hidden_swap_renewal_minus_damaged_copy_positive_adjusted_lower.

## Retained diagnostics

| Additional replacements | Unchanged renewal function, % | Swapped renewal function, % | Distinct renewal packets, % | Joint functional exact retention, % |
|---|---:|---:|---:|---:|
| 1 | 97.32 | 96.43 | 100.00 | 91.96 |
| 4 | 91.96 | 95.54 | 100.00 | 85.71 |
| 8 | 89.29 | 91.96 | 100.00 | 83.04 |
| 16 | 93.75 | 91.96 | 100.00 | 83.04 |

| Variant | Terminal exact self-retention, % | Uninterrupted renewal, % [95% interval] |
|---|---:|---:|
| unchanged | 93.75 | 80.36 |
| hidden_swap | 91.96 | 85.71 |

Record distinctness and retention are separate from function. The joint exact-retention event requires both original records to be reproduced and both checkpoint bodies and fresh readers to function. Uninterrupted function requires all sixteen bodies and the terminal reader to pass. None of these diagnostics, an intermediate horizon or a subgroup can rescue a failed primary.

All results average eligible packets and eight future branches within each network, then weight nonempty networks equally. Inference resamples complete network rows. The 24 development bases and dose feasibility were already exposed; fresh current and future tapes do not make this independent-base confirmation. Current equivalence is finite and applies to cohort means, not every individual pair.

Both packets have identical visible blocks, weight histograms and record norms; shared base weights remain fixed and effective total norms are retained. Reconstruction uses the original body-only writer without a teacher or ancestral record. Copy controls retain their lower computational cost.

No private data, code, text, citations or trained state entered this study. H004/H005/H006/H007 outcomes remain unchanged. No manuscript edit, release or later experiment is launched here.

Audit passed: True. Source networks: 1.

Engineering forced all eight full-length branches using excluded seed 12900 to exercise the pipeline. It cannot establish population equivalence or a scientific durability verdict.
