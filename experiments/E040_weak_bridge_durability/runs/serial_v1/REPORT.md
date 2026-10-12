# E040 weak repair through 32 damaged rebuilds

**LONG_RENEWAL_NOT_QUALIFIED**

**Durability: DURABILITY_NOT_ESTABLISHED**

**Relative benefit: LONG_RENEWAL_BENEFIT_ESTABLISHED**

32 blocks, 512 lineages; thirty-two damaged replacements.

Primary h32 gain: **35.55 [29.49, 41.41] percentage points**; lower bound must exceed five.

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
| 3 | standard_preserve | 100.00 [100.00, 100.00] | 97.85 [95.70, 99.41] | 99.41 [98.44, 100.00] | 24/24 |
| 3 | standard_rewrite | 99.80 [99.41, 100.00] | 98.05 [96.09, 99.41] | 99.22 [98.24, 100.00] | 24/24 |
| 3 | bridge_preserve | 100.00 [100.00, 100.00] | 98.05 [95.90, 99.61] | 99.41 [98.44, 100.00] | 24/24 |
| 3 | bridge_rewrite | 100.00 [100.00, 100.00] | 98.05 [96.09, 99.41] | 99.61 [98.83, 100.00] | 24/24 |
| 3 | contrast_preserve | 98.63 [97.27, 99.80] | 87.30 [83.79, 90.62] | 97.46 [95.90, 98.83] | 24/24 |
| 3 | bridge_read_blocked | 98.44 [96.88, 99.61] | 83.40 [79.49, 87.11] | 96.48 [94.73, 98.05] | 24/24 |
| 3 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | masked_copy | 98.63 [97.27, 99.80] | 86.72 [83.01, 90.23] | 97.46 [95.90, 98.83] | 24/24 |
| 8 | standard_preserve | 93.95 [91.80, 95.90] | 82.42 [78.91, 85.94] | 91.41 [88.87, 93.75] | 24/24 |
| 8 | standard_rewrite | 88.48 [84.57, 92.19] | 77.15 [72.85, 81.05] | 85.35 [81.25, 89.06] | 24/24 |
| 8 | bridge_preserve | 99.02 [97.85, 99.80] | 94.92 [92.97, 96.68] | 99.02 [97.85, 99.80] | 24/24 |
| 8 | bridge_rewrite | 98.24 [96.88, 99.41] | 94.73 [92.58, 96.68] | 97.85 [96.48, 99.02] | 24/24 |
| 8 | contrast_preserve | 1.37 [0.20, 2.73] | 0.00 [0.00, 0.00] | 0.78 [0.00, 1.95] | 12/24 |
| 8 | bridge_read_blocked | 1.17 [0.20, 2.54] | 0.20 [0.00, 0.59] | 0.59 [0.00, 1.56] | 12/24 |
| 8 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 8 | masked_copy | 1.37 [0.20, 2.73] | 0.00 [0.00, 0.00] | 0.78 [0.00, 1.95] | 12/24 |
| 16 | standard_preserve | 62.50 [58.40, 66.60] | 51.76 [46.68, 56.84] | 62.50 [58.20, 66.80] | 18/24 |
| 16 | standard_rewrite | 48.83 [44.14, 53.52] | 39.45 [35.35, 43.55] | 47.66 [42.58, 52.54] | 18/24 |
| 16 | bridge_preserve | 92.19 [89.45, 94.73] | 85.74 [82.23, 89.26] | 91.02 [87.89, 93.75] | 24/24 |
| 16 | bridge_rewrite | 92.58 [89.84, 95.12] | 89.65 [86.33, 92.58] | 92.38 [89.26, 95.12] | 24/24 |
| 16 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 16 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 24 | standard_preserve | 49.41 [44.92, 53.71] | 41.99 [37.50, 46.48] | 48.44 [44.14, 52.73] | 18/24 |
| 24 | standard_rewrite | 33.20 [28.91, 37.50] | 29.88 [26.17, 33.59] | 31.84 [27.54, 36.13] | 18/24 |
| 24 | bridge_preserve | 83.01 [79.49, 86.33] | 77.34 [73.83, 80.66] | 82.42 [79.10, 85.74] | 24/24 |
| 24 | bridge_rewrite | 89.65 [86.52, 92.58] | 87.30 [83.40, 91.02] | 89.06 [85.55, 92.19] | 24/24 |
| 24 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 24 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 24 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 24 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 24 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 32 | standard_preserve | 39.45 [35.16, 43.95] | 35.55 [31.25, 39.84] | 38.48 [34.38, 42.58] | 18/24 |
| 32 | standard_rewrite | 21.68 [18.16, 25.20] | 20.12 [16.60, 23.63] | 21.09 [17.77, 24.41] | 15/24 |
| 32 | bridge_preserve | 75.98 [72.46, 79.49] | 71.09 [66.99, 75.00] | 75.20 [71.88, 78.52] | 24/24 |
| 32 | bridge_rewrite | 88.67 [85.55, 91.61] | 86.33 [82.62, 89.84] | 88.67 [85.74, 91.41] | 24/24 |
| 32 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 32 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 32 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 32 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 32 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |

Prespecified secondary repair rescue versus pure contrast: **71.09 [66.99, 75.00] percentage points**.
Secondary lower bound above ten points: True.

Durability requirements:
- h8_intact_both_cue_lower_above_075: True
- h8_scattered_both_cue_lower_above_075: True
- h8_original_24_gates: True
- h16_intact_both_cue_lower_above_075: True
- h16_scattered_both_cue_lower_above_075: True
- h16_original_24_gates: True
- h24_intact_both_cue_lower_above_075: True
- h24_scattered_both_cue_lower_above_075: False
- h24_original_24_gates: True
- h32_intact_both_cue_lower_above_075: False
- h32_scattered_both_cue_lower_above_075: False
- h32_original_24_gates: True
- h16_above_bridge_read_blocked_by_010: True
- h16_above_bridge_write_blocked_by_010: True
- h32_above_bridge_read_blocked_by_010: True
- h32_above_bridge_write_blocked_by_010: True
- initial_normalized_original_24_gates: True

Fresh independent histories; no earlier cases pooled. Bridge preservation remains the frozen candidate. Rewriting is secondary and cannot replace a failed candidate; its blocked variants are not matched here. All controls, receiver panels, pointwise secondary contrasts, body scores and changes from h1 are in summary.json. The h8/h16 durability requirements are retained and extended to h24/h32; this does not establish indefinite maintenance. Technical outcomes cannot decide scientific claims.
