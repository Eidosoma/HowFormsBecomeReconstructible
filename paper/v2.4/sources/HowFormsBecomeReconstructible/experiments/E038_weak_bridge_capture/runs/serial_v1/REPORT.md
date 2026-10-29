# E038 weak-bridge cue-sensitive rebuilding

**WEAK_BRIDGE_BENEFIT_ESTABLISHED**

**Durability: DURABLE_THROUGH_16_RENEWALS**

32 blocks, 512 lineages; sixteen damaged replacements.

Primary h16 gain: **24.22 [19.34, 28.71] percentage points**.

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
| 3 | standard_preserve | 99.80 [99.41, 100.00] | 97.27 [95.70, 98.63] | 99.61 [98.83, 100.00] | 24/24 |
| 3 | standard_rewrite | 99.22 [98.24, 100.00] | 97.46 [95.90, 98.83] | 99.22 [98.24, 100.00] | 24/24 |
| 3 | bridge_preserve | 99.61 [98.83, 100.00] | 97.85 [96.29, 99.22] | 99.61 [98.83, 100.00] | 24/24 |
| 3 | bridge_rewrite | 99.22 [98.24, 100.00] | 98.05 [96.48, 99.41] | 99.02 [97.85, 100.00] | 24/24 |
| 3 | contrast_preserve | 98.83 [97.66, 99.80] | 85.74 [82.42, 88.87] | 98.44 [97.07, 99.61] | 24/24 |
| 3 | bridge_read_blocked | 98.44 [97.07, 99.61] | 83.79 [80.27, 86.91] | 97.66 [96.09, 99.02] | 24/24 |
| 3 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | masked_copy | 98.83 [97.66, 99.80] | 85.74 [82.42, 88.87] | 98.44 [97.07, 99.61] | 24/24 |
| 8 | standard_preserve | 93.55 [90.82, 96.29] | 82.42 [77.54, 87.11] | 92.97 [90.04, 95.70] | 24/24 |
| 8 | standard_rewrite | 91.21 [88.28, 94.14] | 80.47 [76.17, 84.57] | 90.43 [87.50, 93.36] | 24/24 |
| 8 | bridge_preserve | 98.05 [96.68, 99.22] | 92.77 [89.84, 95.31] | 97.07 [95.31, 98.63] | 24/24 |
| 8 | bridge_rewrite | 97.66 [96.29, 98.83] | 92.38 [89.65, 94.92] | 97.07 [95.51, 98.44] | 24/24 |
| 8 | contrast_preserve | 1.95 [0.59, 3.71] | 0.59 [0.00, 1.56] | 2.15 [0.59, 3.91] | 12/24 |
| 8 | bridge_read_blocked | 1.17 [0.00, 2.73] | 0.78 [0.00, 1.76] | 1.76 [0.59, 3.12] | 12/24 |
| 8 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 8 | masked_copy | 1.95 [0.59, 3.71] | 0.59 [0.00, 1.56] | 1.95 [0.39, 3.71] | 12/24 |
| 16 | standard_preserve | 68.75 [63.28, 74.22] | 57.81 [53.32, 62.11] | 66.41 [60.74, 72.07] | 18/24 |
| 16 | standard_rewrite | 47.66 [42.97, 52.15] | 40.43 [36.91, 43.75] | 47.07 [42.38, 51.76] | 18/24 |
| 16 | bridge_preserve | 89.65 [86.13, 92.97] | 82.03 [77.93, 85.94] | 89.45 [86.72, 92.19] | 24/24 |
| 16 | bridge_rewrite | 94.14 [91.41, 96.68] | 89.45 [85.74, 92.97] | 93.95 [91.21, 96.48] | 24/24 |
| 16 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 11/24 |
| 16 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 16 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |

Prespecified secondary repair rescue versus pure contrast: **82.03 [77.93, 85.94] percentage points**.
Secondary lower bound above ten points: True.

Durability requirements:
- h8_intact_both_cue_lower_above_075: True
- h8_scattered_both_cue_lower_above_075: True
- h8_original_24_gates: True
- h16_intact_both_cue_lower_above_075: True
- h16_scattered_both_cue_lower_above_075: True
- h16_original_24_gates: True
- h16_above_bridge_read_blocked_by_010: True
- h16_above_bridge_write_blocked_by_010: True
- initial_normalized_original_24_gates: True

Fresh independent histories; no earlier cases pooled. The joint primary and absolute durability are separate. All controls, receiver panels, pointwise secondary contrasts, body scores and changes from h1 are in summary.json. A finite sixteen-renewal result does not establish indefinite maintenance. Technical outcomes cannot decide scientific claims.
