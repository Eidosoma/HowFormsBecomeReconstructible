# E041 full rewriting through 32 damaged rebuilds

**FULL_REWRITING_QUALIFIED**

**Durability: DURABLE_THROUGH_32_RENEWALS**

**Relative benefit: REWRITING_BENEFIT_ESTABLISHED**

32 blocks, 512 lineages; thirty-two damaged replacements.

Primary h32 gain: **10.94 [6.84, 15.23] percentage points**; lower bound must exceed five.

Full qualification requires this relative gain and all seventeen durability requirements.

| Generation | Policy | Normalized intact % [95%] | Scattered | Square | Original gates |
| --- | --- | --- | --- | --- | --- |
| 0 | initial | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | standard_preserve | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | standard_rewrite | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | bridge_preserve | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | bridge_rewrite | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | contrast_preserve | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | bridge_read_blocked | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 1 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | masked_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | bridge_rewrite_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 1 | bridge_rewrite_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | standard_preserve | 100.00 [100.00, 100.00] | 96.09 [94.34, 97.66] | 99.80 [99.41, 100.00] | 24/24 |
| 3 | standard_rewrite | 99.61 [99.02, 100.00] | 96.09 [94.34, 97.85] | 99.61 [99.02, 100.00] | 24/24 |
| 3 | bridge_preserve | 100.00 [100.00, 100.00] | 96.29 [94.53, 97.85] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | bridge_rewrite | 99.61 [99.02, 100.00] | 96.29 [94.53, 97.85] | 99.61 [99.02, 100.00] | 24/24 |
| 3 | contrast_preserve | 98.44 [97.07, 99.41] | 82.81 [79.10, 86.52] | 97.46 [95.70, 99.02] | 24/24 |
| 3 | bridge_read_blocked | 98.24 [96.68, 99.41] | 79.49 [75.59, 83.20] | 96.88 [94.92, 98.63] | 24/24 |
| 3 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | masked_copy | 98.44 [97.07, 99.41] | 82.81 [79.10, 86.52] | 97.46 [95.70, 99.02] | 24/24 |
| 3 | bridge_rewrite_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | bridge_rewrite_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | standard_preserve | 93.55 [91.02, 95.90] | 84.57 [81.05, 87.70] | 92.77 [89.84, 95.51] | 24/24 |
| 8 | standard_rewrite | 88.09 [85.16, 91.02] | 81.25 [77.34, 84.77] | 87.89 [85.16, 90.62] | 24/24 |
| 8 | bridge_preserve | 98.44 [97.26, 99.61] | 95.51 [93.16, 97.66] | 98.24 [96.68, 99.61] | 24/24 |
| 8 | bridge_rewrite | 98.63 [97.46, 99.61] | 94.92 [92.19, 97.27] | 97.27 [94.73, 99.22] | 24/24 |
| 8 | contrast_preserve | 2.54 [1.17, 4.30] | 0.98 [0.00, 2.15] | 2.34 [0.78, 4.10] | 12/24 |
| 8 | bridge_read_blocked | 2.34 [0.98, 3.91] | 0.78 [0.00, 1.76] | 1.95 [0.59, 3.52] | 12/24 |
| 8 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 8 | masked_copy | 2.54 [1.17, 4.30] | 0.98 [0.00, 2.15] | 2.34 [0.78, 4.10] | 12/24 |
| 8 | bridge_rewrite_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | bridge_rewrite_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | standard_preserve | 71.09 [66.99, 75.00] | 62.70 [58.20, 66.99] | 70.90 [66.60, 75.00] | 19/24 |
| 16 | standard_rewrite | 49.80 [45.70, 53.71] | 42.19 [37.89, 46.48] | 47.46 [42.97, 51.95] | 18/24 |
| 16 | bridge_preserve | 93.36 [90.62, 95.90] | 88.87 [85.35, 92.19] | 93.16 [90.43, 95.70] | 24/24 |
| 16 | bridge_rewrite | 95.90 [93.55, 97.85] | 91.41 [88.48, 94.14] | 96.29 [94.14, 98.05] | 24/24 |
| 16 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.20 [0.00, 0.59] | 12/24 |
| 16 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 16 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | bridge_rewrite_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | bridge_rewrite_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 24 | standard_preserve | 52.15 [47.27, 57.03] | 46.68 [41.80, 51.56] | 51.17 [46.09, 56.05] | 18/24 |
| 24 | standard_rewrite | 32.42 [28.12, 36.52] | 28.71 [24.61, 32.62] | 29.69 [25.20, 33.98] | 18/24 |
| 24 | bridge_preserve | 87.50 [83.59, 91.21] | 81.25 [77.34, 84.96] | 86.13 [81.84, 90.04] | 24/24 |
| 24 | bridge_rewrite | 91.99 [89.06, 94.53] | 89.84 [86.52, 92.77] | 91.60 [88.28, 94.34] | 24/24 |
| 24 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 24 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 24 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 24 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 24 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 24 | bridge_rewrite_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 24 | bridge_rewrite_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 32 | standard_preserve | 43.16 [38.48, 48.05] | 37.30 [32.42, 42.38] | 42.58 [38.09, 47.46] | 18/24 |
| 32 | standard_rewrite | 23.05 [20.12, 26.17] | 20.12 [16.99, 23.44] | 23.24 [19.73, 26.76] | 15/24 |
| 32 | bridge_preserve | 78.71 [74.80, 82.42] | 72.66 [68.36, 76.76] | 77.73 [73.24, 82.03] | 24/24 |
| 32 | bridge_rewrite | 89.45 [86.52, 92.19] | 83.59 [80.66, 86.33] | 88.67 [85.94, 91.21] | 24/24 |
| 32 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 32 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 11/24 |
| 32 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 32 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 32 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 32 | bridge_rewrite_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 32 | bridge_rewrite_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |

Prespecified secondary repair rescue versus pure contrast: **72.66 [68.36, 76.76] percentage points**.
Secondary lower bound above ten points: True.

Durability requirements:
- h8_intact_both_cue_lower_above_075: True
- h8_scattered_both_cue_lower_above_075: True
- h8_original_24_gates: True
- h16_intact_both_cue_lower_above_075: True
- h16_scattered_both_cue_lower_above_075: True
- h16_original_24_gates: True
- h24_intact_both_cue_lower_above_075: True
- h24_scattered_both_cue_lower_above_075: True
- h24_original_24_gates: True
- h32_intact_both_cue_lower_above_075: True
- h32_scattered_both_cue_lower_above_075: True
- h32_original_24_gates: True
- h16_above_bridge_rewrite_read_blocked_by_010: True
- h16_above_bridge_rewrite_write_blocked_by_010: True
- h32_above_bridge_rewrite_read_blocked_by_010: True
- h32_above_bridge_rewrite_write_blocked_by_010: True
- initial_normalized_original_24_gates: True

Fresh independent histories; no earlier cases pooled. Full bridge rewriting is the frozen candidate, with matched reading-blocked and writing-blocked controls. E040 results motivated this fresh test; prior conclusions remain unchanged. All controls, receiver panels, pointwise secondary contrasts, body scores and changes from h1 are in summary.json. Durability is required at h8/h16/h24/h32; this does not establish indefinite maintenance. Technical outcomes cannot decide scientific claims.
