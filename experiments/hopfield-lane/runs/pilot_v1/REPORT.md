# H001 development results

12 independent random-base blocks; four founders and four descendants per founder; 16 replacements.
All intervals below are exploratory, pointwise 95% whole-block bootstrap intervals. This is a feasibility screen, not a fresh-cohort confirmation.

## Capture

| Arm | Terminal completion |
|---|---:|
| renewal | 59.90% [53.12, 66.15] |
| foreign | 1.04% [0.00, 3.12] |
| scrambled | 0.00% [0.00, 0.00] |
| erased | 2.08% [0.52, 3.65] |
| read_off | 3.12% [1.04, 5.73] |
| write_off | 2.08% [0.52, 3.65] |
| protected_copy | 84.90% [81.25, 88.02] |
| damaged_copy | 2.08% [0.52, 3.65] |
| writer_scrambled | 0.00% [0.00, 0.00] |

Contrasts are paired percentage-point differences:

| Contrast | Difference [interval] |
|---|---:|
| renewal_minus_foreign | 58.85% [50.00, 66.15] |
| renewal_minus_scrambled | 59.90% [53.12, 66.15] |
| renewal_minus_erased | 57.81% [50.52, 64.06] |
| renewal_minus_read_off | 56.77% [51.03, 61.98] |
| renewal_minus_write_off | 57.81% [51.56, 63.54] |
| renewal_minus_protected_copy | -25.00% [-30.21, -19.79] |
| renewal_minus_damaged_copy | 57.81% [51.56, 63.54] |
| renewal_minus_writer_scrambled | 59.90% [53.12, 66.15] |

Initial completion: 83.85% [77.60, 90.10]. Last rebuilding-body completion: 64.58% [57.81, 71.35].
Founder stability under another 24 teaching/formation sweeps: 1.000. Distinct observed founders by block: [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4].

## Function

| Arm | Terminal completion |
|---|---:|
| renewal | 43.23% [35.94, 50.52] |
| foreign | 16.15% [10.42, 21.88] |
| scrambled | 0.00% [0.00, 0.00] |
| erased | 0.52% [0.00, 1.56] |
| read_off | 0.00% [0.00, 0.00] |
| write_off | 0.00% [0.00, 0.00] |
| protected_copy | 80.73% [77.60, 83.85] |
| damaged_copy | 0.00% [0.00, 0.00] |
| writer_scrambled | 0.52% [0.00, 1.56] |

Contrasts are paired percentage-point differences:

| Contrast | Difference [interval] |
|---|---:|
| renewal_minus_foreign | 27.08% [16.15, 38.02] |
| renewal_minus_scrambled | 43.23% [35.94, 50.52] |
| renewal_minus_erased | 42.71% [35.42, 49.48] |
| renewal_minus_read_off | 43.23% [35.94, 50.52] |
| renewal_minus_write_off | 43.23% [35.94, 50.52] |
| renewal_minus_protected_copy | -37.50% [-44.79, -29.69] |
| renewal_minus_damaged_copy | 43.23% [35.94, 50.52] |
| renewal_minus_writer_scrambled | 42.71% [34.90, 50.00] |

Initial completion: 84.38% [80.21, 88.54]. Last rebuilding-body completion: 43.23% [34.90, 51.56].
Founder stability under another 24 teaching/formation sweeps: 1.000. Distinct observed founders by block: [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4].

## Reciprocal repair

| Arm | Completion | Agreement |
|---|---:|---:|
| damaged | 79.69% [75.52, 83.33] | 82.13% [78.11, 85.81] |
| live_kept | 79.17% [75.52, 83.33] | 79.60% [75.50, 83.71] |
| live_scrambled | 35.42% [28.65, 41.68] | 67.09% [63.62, 70.41] |
| fixed_kept | 80.21% [77.08, 83.33] | 80.09% [76.97, 83.19] |
| fixed_scrambled | 72.92% [69.27, 76.56] | 73.67% [70.38, 77.01] |
| read_off | 12.50% [7.29, 17.71] | 68.26% [64.63, 72.29] |

| Contrast | Completion difference [interval] |
|---|---:|
| live_kept_minus_damaged | -0.52% [-6.77, 6.77] |
| live_kept_minus_live_scrambled | 43.75% [34.90, 52.08] |
| live_kept_minus_fixed_kept | -1.04% [-4.17, 2.08] |
| fixed_kept_minus_damaged | 0.52% [-4.69, 5.73] |
| live_kept_minus_read_off | 66.67% [59.90, 73.44] |

## Continuous transmission screen

Each entry is one deterministic parameter setting at dt=0.0125. True/false is a bounded-model outcome; these settings are not independent experimental replicates.

| Self | Contact | Immature/open | Prepared/open | Immature/immediate pause | Edited relay | Sham reverses | Blocked relay/edit |
|---:|---:|---|---|---|---|---|---|
| 1.2 | 0.2 | False | False | False | False | False | False |
| 1.2 | 0.4 | False | False | False | False | False | False |
| 1.2 | 0.6 | False | False | False | True | False | False |
| 1.2 | 0.8 | False | False | False | True | False | False |
| 1.6 | 0.2 | False | False | False | False | False | False |
| 1.6 | 0.4 | False | False | False | False | False | False |
| 1.6 | 0.6 | False | True | False | True | False | False |
| 1.6 | 0.8 | False | True | False | True | False | False |

Maximum state discrepancy on halving dt: 1.82076e-06. Readiness labels agree: True; editing labels agree: True.

## Interpretation boundary

The binary writer is a supplied, redundant coactivity encoder. Dense connectivity, input sites, timing and coordinate conventions are also supplied. Successful renewal would establish a mechanism specimen under these conditions; it would not establish spontaneous useful competence or evolved reconstruction machinery. Capture and functional teaching are separate experiments. The continuous model does not reproduce molecular regulation or the original cellular time scales.

Terminal fresh readers and the last rebuilding bodies use different independent births. Their aggregate difference alone is not evidence for recovery along the same body history. Copying comparisons have equal packet allocation, not equal computation cost. Correlation-preserving and address controls test the stated interfaces only. No pilot result has been added to the forms manuscript.
