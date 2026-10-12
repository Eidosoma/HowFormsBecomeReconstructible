# H007: coherent hidden-pattern transmission

PROSPECTIVE_FEASIBILITY_SCREEN_ON_DEVELOPMENT_CHECKPOINTS.

**Decision: FEASIBILITY_CANDIDATE.** Nominated hidden-pair dose: **8**.

This is a one-replacement feasibility screen. Every dose uses the original body-only writer, fixed gain-4 reader and paired damage/read tapes. Current enrollment was sealed before any replacement observations. All four doses and their failures are retained.

| Hidden pairs swapped | Matched packets | Nonempty networks | Unchanged current, % [95% interval] | Swapped current, % [95% interval] | Current gates |
|---|---:|---:|---:|---:|---|
| 1 | 267 | 24 | 97.66 [97.44, 97.89] | 97.56 [97.28, 97.85] | True |
| 2 | 255 | 24 | 97.62 [97.36, 97.87] | 97.46 [97.17, 97.75] | True |
| 4 | 249 | 24 | 97.64 [97.37, 97.89] | 97.57 [97.28, 97.85] | True |
| 8 | 244 | 24 | 97.67 [97.40, 97.93] | 97.87 [97.63, 98.10] | True |

Current success and all four output differences must have 97.5% bootstrap intervals inside ±1 percentage point, with at least 64 matches across 16 networks and ≥95% success in both variants. The wider equivalence intervals account for four screened doses; the table shows marginal 95% intervals.

| Hidden pairs | Joint functional exact retention, % [95% interval] | Adjusted lower, % | Renewal minus read-off, points | Renewal minus write-off, points | Full screen passes |
|---|---:|---:|---:|---:|---|
| 1 | 95.02 [94.00, 95.95] | 93.64 | 95.02 [94.00, 95.95] | 95.02 [94.00, 95.95] | True |
| 2 | 94.66 [93.47, 95.72] | 93.05 | 94.66 [93.47, 95.72] | 94.66 [93.47, 95.72] | True |
| 4 | 94.44 [93.55, 95.23] | 93.24 | 94.44 [93.55, 95.23] | 94.44 [93.55, 95.23] | True |
| 8 | 94.15 [93.04, 95.16] | 92.65 | 94.15 [93.04, 95.16] | 94.15 [93.04, 95.16] | True |

Joint retention requires both intended, distinct packets to be reproduced exactly and both rebuilt bodies and fresh readers to pass the original function threshold. The mean must reach 80%, its adjusted lower bound 70%, and each read/write route contrast must reach 50 points with a positive adjusted lower bound. Bounds use quantile .05/12. Trials and packets are averaged within each network before equal network weighting. Different doses can have different matched cohorts.

## Dose 1

Failed current gates: none.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | -0.10 | [-0.35, 0.12] |
| output_0 | -0.10 | [-0.43, 0.22] |
| output_1 | -0.10 | [-0.43, 0.22] |
| output_2 | -0.10 | [-0.56, 0.28] |
| output_3 | -0.10 | [-0.56, 0.28] |

Failed full-screen gates: none.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 96.32 | 96.87 | 98.92 | 98.72 | 100.00 | 95.02 |
| restored | 96.32 | 96.32 | 98.92 | 0.00 | 0.00 | 0.00 |
| foreign | 5.50 | 5.39 | 0.00 | 0.00 | 90.56 | 0.00 |
| protected_copy | 97.20 | 97.67 | 100.00 | 100.00 | 100.00 | 93.72 |
| damaged_copy | 98.60 | 98.81 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Dose 2

Failed current gates: none.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | -0.16 | [-0.42, 0.10] |
| output_0 | -0.06 | [-0.45, 0.32] |
| output_1 | -0.06 | [-0.45, 0.32] |
| output_2 | -0.24 | [-0.69, 0.15] |
| output_3 | -0.24 | [-0.69, 0.15] |

Failed full-screen gates: none.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 96.41 | 96.94 | 98.99 | 98.67 | 100.00 | 94.66 |
| restored | 96.41 | 96.41 | 98.99 | 0.00 | 0.00 | 0.00 |
| foreign | 5.99 | 5.78 | 0.00 | 0.00 | 90.73 | 0.00 |
| protected_copy | 97.21 | 97.91 | 100.00 | 100.00 | 100.00 | 92.96 |
| damaged_copy | 98.62 | 98.99 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Dose 4

Failed current gates: none.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | -0.06 | [-0.44, 0.26] |
| output_0 | -0.00 | [-0.50, 0.48] |
| output_1 | -0.00 | [-0.50, 0.48] |
| output_2 | -0.10 | [-0.90, 0.49] |
| output_3 | -0.10 | [-0.90, 0.49] |

Failed full-screen gates: none.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 96.30 | 97.51 | 98.81 | 98.98 | 100.00 | 94.44 |
| restored | 96.30 | 96.30 | 98.81 | 0.00 | 0.00 | 0.00 |
| foreign | 5.96 | 5.67 | 0.00 | 0.00 | 90.54 | 0.00 |
| protected_copy | 97.33 | 98.16 | 100.00 | 100.00 | 100.00 | 92.49 |
| damaged_copy | 98.59 | 99.09 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Dose 8

Failed current gates: none.

| Current difference, swapped minus unchanged | Mean, points | Adjusted equivalence interval, points |
|---|---:|---:|
| success | 0.20 | [-0.16, 0.56] |
| output_0 | 0.31 | [-0.21, 0.84] |
| output_1 | 0.31 | [-0.21, 0.84] |
| output_2 | 0.09 | [-0.50, 0.59] |
| output_3 | 0.09 | [-0.50, 0.59] |

Failed full-screen gates: none.

| Arm | Unchanged fresh function, % | Swapped fresh function, % | Unchanged exact self-retention, % | Swapped exact self-retention, % | Distinct packets, % | Joint event, % |
|---|---:|---:|---:|---:|---:|---:|
| renewal | 96.34 | 97.92 | 98.86 | 98.89 | 100.00 | 94.15 |
| restored | 96.34 | 96.34 | 98.86 | 0.00 | 0.00 | 0.00 |
| foreign | 5.60 | 5.29 | 0.00 | 0.00 | 90.90 | 0.00 |
| protected_copy | 97.31 | 98.70 | 100.00 | 100.00 | 100.00 | 92.04 |
| damaged_copy | 98.62 | 99.92 | 0.00 | 0.00 | 100.00 | 0.00 |
| read_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| write_off | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

All source networks were already exposed in H003 development; H004 confirmation was excluded. Current validation is a finite, cohort-level observer and does not guarantee equality for every packet. Sources without an exact opposing observation pair, fully correct visible output, or eight hidden sites of each sign are excluded by the same structural rule at every dose.

Swaps preserve the full weight histogram, norm, visible record block and coordinate-permutation invariants. Shared base weights remain fixed; base-plus-record norms are retained separately. The intervention changes more edges than H006 and is not an equal-size comparison with its edge flips.

Exact self-retention is deliberately stronger than functional continuation. A passed screen establishes feasibility for one replacement, not different long-term durability, useful reciprocal repair, discovered competence or superiority to protected copying. Failed doses cannot be rescued by another endpoint. No sixteen-replacement study is launched here and H005/H006 verdicts remain unchanged.

Complete block rows, every gate, all route controls and independently replayed raw observations are retained. No private code, data, trained states or text entered the screen. No manuscript was edited.

Retained audit passed: True. Number of source networks: 24.
