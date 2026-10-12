# E036 cue-sensitive serial rebuilding

**SERIAL_CAPTURE_BENEFIT_NOT_ESTABLISHED**

**Durability: DURABILITY_NOT_ESTABLISHED**

32 blocks, 512 lineages; sixteen damaged replacements.

Primary h16 gain: **-56.64 [-60.55, -52.54] percentage points**.

| Generation | Policy | Normalized intact % [95%] | Scattered | Square | Original gates |
| --- | --- | --- | --- | --- | --- |
| 0 | initial | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | standard_preserve | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | standard_rewrite | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | contrast_preserve | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | contrast_rewrite | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | original_standard_preserve | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | contrast_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 1 | contrast_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 1 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 1 | masked_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | standard_preserve | 100.00 [100.00, 100.00] | 96.68 [94.92, 98.24] | 99.61 [99.02, 100.00] | 24/24 |
| 3 | standard_rewrite | 100.00 [100.00, 100.00] | 96.48 [94.53, 98.24] | 99.41 [98.44, 100.00] | 24/24 |
| 3 | contrast_preserve | 99.61 [99.02, 100.00] | 85.74 [82.23, 88.87] | 99.02 [98.05, 99.80] | 24/24 |
| 3 | contrast_rewrite | 99.61 [99.02, 100.00] | 85.94 [83.01, 88.87] | 99.22 [98.44, 99.80] | 24/24 |
| 3 | original_standard_preserve | 99.80 [99.41, 100.00] | 95.12 [92.97, 97.07] | 99.41 [98.63, 100.00] | 24/24 |
| 3 | contrast_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | contrast_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | masked_copy | 99.61 [99.02, 100.00] | 85.55 [82.03, 88.87] | 98.83 [97.66, 99.80] | 24/24 |
| 8 | standard_preserve | 90.62 [87.89, 93.16] | 81.64 [77.93, 85.16] | 91.21 [88.48, 93.75] | 24/24 |
| 8 | standard_rewrite | 86.52 [83.40, 89.45] | 76.56 [72.66, 80.27] | 85.35 [81.84, 88.67] | 24/24 |
| 8 | contrast_preserve | 0.98 [0.00, 2.15] | 0.00 [0.00, 0.00] | 1.95 [0.59, 3.71] | 12/24 |
| 8 | contrast_rewrite | 1.76 [0.59, 3.32] | 0.00 [0.00, 0.00] | 2.54 [0.78, 4.69] | 0/24 |
| 8 | original_standard_preserve | 77.73 [74.02, 81.45] | 67.38 [62.50, 71.88] | 77.73 [74.22, 81.25] | 22/24 |
| 8 | contrast_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | contrast_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 8 | masked_copy | 0.98 [0.00, 2.15] | 0.00 [0.00, 0.00] | 1.95 [0.59, 3.71] | 12/24 |
| 16 | standard_preserve | 64.84 [61.33, 68.16] | 56.64 [52.54, 60.55] | 64.65 [60.74, 68.36] | 18/24 |
| 16 | standard_rewrite | 45.90 [40.82, 50.78] | 39.06 [34.77, 43.36] | 44.73 [39.65, 49.61] | 18/24 |
| 16 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | contrast_rewrite | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | original_standard_preserve | 38.67 [34.18, 43.16] | 32.81 [28.12, 37.30] | 38.48 [34.38, 42.38] | 18/24 |
| 16 | contrast_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | contrast_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 16 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |

Durability requirements:
- h8_intact_both_cue_lower_above_075: False
- h8_scattered_both_cue_lower_above_075: False
- h8_original_24_gates: False
- h16_intact_both_cue_lower_above_075: False
- h16_scattered_both_cue_lower_above_075: False
- h16_original_24_gates: False
- h16_above_contrast_read_blocked_by_010: False
- h16_above_contrast_write_blocked_by_010: False
- initial_normalized_original_24_gates: True

Fresh independent histories; no earlier cases pooled. The joint primary and absolute durability are separate. All controls, receiver panels, pointwise secondary contrasts, body scores and changes from h1 are in summary.json. A finite sixteen-renewal result does not establish indefinite maintenance. Technical outcomes cannot decide scientific claims.
