# H007: coherent hidden-pattern transmission

ENGINEERING_BENCHMARK.

**Decision: ENGINEERING_ONLY.** Nominated hidden-pair dose: **None**.

This is a one-replacement feasibility screen. Every dose uses the original body-only writer, fixed gain-4 reader and paired damage/read tapes. Current enrollment was sealed before any replacement observations. All four doses and their failures are retained.

| Hidden pairs swapped | Matched packets | Nonempty networks | Unchanged current, % [95% interval] | Swapped current, % [95% interval] | Current gates |
|---|---:|---:|---:|---:|---|
| 1 | 14 | 1 | 97.43 | 97.66 | False |
| 2 | 12 | 1 | 97.66 | 97.40 | False |
| 4 | 12 | 1 | 97.27 | 97.79 | False |
| 8 | 14 | 1 | 97.32 | 98.21 | False |

Current success and all four output differences must have 97.5% bootstrap intervals inside ±1 percentage point, with at least 64 matches across 16 networks and ≥95% success in both variants. The wider equivalence intervals account for four screened doses; the table shows marginal 95% intervals.

| Hidden pairs | Joint functional exact retention, % [95% interval] | Adjusted lower, % | Renewal minus read-off, points | Renewal minus write-off, points | Full screen passes |
|---|---:|---:|---:|---:|---|
| 1 | 94.64 | unavailable | 94.64 | 94.64 | False |
| 2 | 95.83 | unavailable | 95.83 | 95.83 | False |
| 4 | 94.79 | unavailable | 94.79 | 94.79 | False |
| 8 | 93.75 | unavailable | 93.75 | 93.75 | False |

Joint retention requires both intended, distinct packets to be reproduced exactly and both rebuilt bodies and fresh readers to pass the original function threshold. The mean must reach 80%, its adjusted lower bound 70%, and each read/write route contrast must reach 50 points with a positive adjusted lower bound. Bounds use quantile .05/12. Trials and packets are averaged within each network before equal network weighting. Different doses can have different matched cohorts.

## Dose 1

Failed current gates: at_least_64_matches, at_least_16_networks, success_equivalent_within_1pp, output_0_equivalent_within_1pp, output_1_equivalent_within_1pp, output_2_equivalent_within_1pp, output_3_equivalent_within_1pp.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | 0.22 | [unavailable, unavailable] |
| output_0 | 0.00 | [unavailable, unavailable] |
| output_1 | 0.00 | [unavailable, unavailable] |
| output_2 | 0.45 | [unavailable, unavailable] |
| output_3 | 0.45 | [unavailable, unavailable] |

Failed full-screen gates: current_passed, joint_functional_retention_lower_bound, renewal_minus_read_off_lower_bound, renewal_minus_write_off_lower_bound.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 95.54 | 95.54 | 99.11 | 98.21 | 100.00 | 94.64 |
| restored | 95.54 | 95.54 | 99.11 | 0.00 | 0.00 | 0.00 |
| foreign | 0.89 | 0.00 | 0.00 | 0.00 | 100.00 | 0.00 |
| protected_copy | 96.43 | 97.32 | 100.00 | 100.00 | 100.00 | 91.07 |
| damaged_copy | 95.54 | 98.21 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Dose 2

Failed current gates: at_least_64_matches, at_least_16_networks, success_equivalent_within_1pp, output_0_equivalent_within_1pp, output_1_equivalent_within_1pp, output_2_equivalent_within_1pp, output_3_equivalent_within_1pp.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | -0.26 | [unavailable, unavailable] |
| output_0 | -0.52 | [unavailable, unavailable] |
| output_1 | -0.52 | [unavailable, unavailable] |
| output_2 | 0.00 | [unavailable, unavailable] |
| output_3 | 0.00 | [unavailable, unavailable] |

Failed full-screen gates: current_passed, joint_functional_retention_lower_bound, renewal_minus_read_off_lower_bound, renewal_minus_write_off_lower_bound.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 95.83 | 96.88 | 98.96 | 100.00 | 100.00 | 95.83 |
| restored | 95.83 | 95.83 | 98.96 | 0.00 | 0.00 | 0.00 |
| foreign | 1.04 | 1.04 | 0.00 | 0.00 | 100.00 | 0.00 |
| protected_copy | 96.88 | 96.88 | 100.00 | 100.00 | 100.00 | 91.67 |
| damaged_copy | 94.79 | 97.92 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Dose 4

Failed current gates: at_least_64_matches, at_least_16_networks, success_equivalent_within_1pp, output_0_equivalent_within_1pp, output_1_equivalent_within_1pp, output_2_equivalent_within_1pp, output_3_equivalent_within_1pp.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | 0.52 | [unavailable, unavailable] |
| output_0 | 0.00 | [unavailable, unavailable] |
| output_1 | 0.00 | [unavailable, unavailable] |
| output_2 | 1.04 | [unavailable, unavailable] |
| output_3 | 1.04 | [unavailable, unavailable] |

Failed full-screen gates: current_passed, joint_functional_retention_lower_bound, renewal_minus_read_off_lower_bound, renewal_minus_write_off_lower_bound.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 94.79 | 97.92 | 98.96 | 100.00 | 100.00 | 94.79 |
| restored | 94.79 | 94.79 | 98.96 | 0.00 | 0.00 | 0.00 |
| foreign | 1.04 | 0.00 | 0.00 | 0.00 | 100.00 | 0.00 |
| protected_copy | 95.83 | 97.92 | 100.00 | 100.00 | 100.00 | 91.67 |
| damaged_copy | 95.83 | 97.92 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Dose 8

Failed current gates: at_least_64_matches, at_least_16_networks, success_equivalent_within_1pp, output_0_equivalent_within_1pp, output_1_equivalent_within_1pp, output_2_equivalent_within_1pp, output_3_equivalent_within_1pp.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | 0.89 | [unavailable, unavailable] |
| output_0 | 0.45 | [unavailable, unavailable] |
| output_1 | 0.45 | [unavailable, unavailable] |
| output_2 | 1.34 | [unavailable, unavailable] |
| output_3 | 1.34 | [unavailable, unavailable] |

Failed full-screen gates: current_passed, joint_functional_retention_lower_bound, renewal_minus_read_off_lower_bound, renewal_minus_write_off_lower_bound.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 95.54 | 96.43 | 99.11 | 100.00 | 100.00 | 93.75 |
| restored | 95.54 | 95.54 | 99.11 | 0.00 | 0.00 | 0.00 |
| foreign | 0.89 | 0.89 | 0.00 | 0.00 | 100.00 | 0.00 |
| protected_copy | 96.43 | 96.43 | 100.00 | 100.00 | 100.00 | 89.29 |
| damaged_copy | 95.54 | 96.43 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

All source networks were already exposed in H003 development; H004 confirmation was excluded. Current validation is a finite, cohort-level observer and does not guarantee equality for every packet. Sources without an exact opposing observation pair, fully correct visible output, or eight hidden sites of each sign are excluded by the same structural rule at every dose.

Swaps preserve the full weight histogram, norm, visible record block and coordinate-permutation invariants. Shared base weights remain fixed; base-plus-record norms are retained separately. The intervention changes more edges than H006 and is not an equal-size comparison with its edge flips.

Exact self-retention is deliberately stronger than functional continuation. A passed screen establishes feasibility for one replacement, not different long-term durability, useful reciprocal repair, discovered competence or superiority to protected copying. Failed doses cannot be rescued by another endpoint. No sixteen-replacement study is launched here and H005/H006 verdicts remain unchanged.

Complete block rows, every gate, all route controls and independently replayed raw observations are retained. No private code, data, trained states or text entered the screen. No manuscript was edited.

Retained audit passed: True. Number of source networks: 1.

Engineering used one excluded network and forced every trial to exercise the complete pipeline. It cannot establish population equivalence or nominate a scientific dose.
