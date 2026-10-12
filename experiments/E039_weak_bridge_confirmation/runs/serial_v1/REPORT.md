# E039 fresh confirmation of weak repair and full rewriting

**JOINT_REPAIR_CONFIRMATION_NOT_ESTABLISHED**

**Durability: DURABLE_THROUGH_16_RENEWALS**

Full confirmation (joint primary and preserved-policy durability): False.

32 blocks, 512 lineages; sixteen damaged replacements.

Primary component 1, repair-preserve minus standard-preserve: **33.40 [27.53, 39.65] percentage points**; lower bound must exceed five.

Primary component 2, repair-rewrite minus repair-preserve: **2.15 [-0.78, 4.88] percentage points**; lower bound must exceed zero.

Both components are required; neither can substitute for the other.

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
| 3 | standard_preserve | 99.02 [97.85, 100.00] | 95.90 [93.75, 97.85] | 98.83 [97.46, 99.80] | 24/24 |
| 3 | standard_rewrite | 98.83 [97.46, 99.80] | 95.90 [93.75, 97.85] | 98.83 [97.46, 99.80] | 24/24 |
| 3 | bridge_preserve | 99.22 [98.24, 100.00] | 96.09 [93.95, 98.05] | 99.22 [98.24, 100.00] | 24/24 |
| 3 | bridge_rewrite | 99.61 [98.83, 100.00] | 96.48 [94.73, 98.05] | 99.41 [98.44, 100.00] | 24/24 |
| 3 | contrast_preserve | 98.05 [96.48, 99.22] | 85.55 [81.25, 89.84] | 97.07 [95.12, 98.63] | 24/24 |
| 3 | bridge_read_blocked | 97.66 [96.09, 99.02] | 82.62 [77.93, 87.11] | 96.68 [94.73, 98.44] | 24/24 |
| 3 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 3 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 3 | masked_copy | 97.85 [96.29, 99.22] | 85.16 [80.86, 89.45] | 96.68 [94.73, 98.44] | 24/24 |
| 8 | standard_preserve | 92.38 [89.45, 95.12] | 83.59 [80.47, 86.52] | 91.21 [88.28, 93.95] | 24/24 |
| 8 | standard_rewrite | 88.28 [85.15, 91.41] | 80.27 [76.76, 83.79] | 85.55 [82.42, 88.67] | 24/24 |
| 8 | bridge_preserve | 96.29 [94.14, 98.24] | 92.38 [89.65, 94.92] | 94.73 [92.58, 96.68] | 24/24 |
| 8 | bridge_rewrite | 97.27 [95.31, 98.83] | 94.14 [91.60, 96.48] | 96.48 [94.53, 98.24] | 24/24 |
| 8 | contrast_preserve | 1.56 [0.39, 2.93] | 0.78 [0.00, 1.95] | 1.17 [0.20, 2.54] | 12/24 |
| 8 | bridge_read_blocked | 1.17 [0.20, 2.54] | 0.78 [0.00, 1.95] | 1.17 [0.20, 2.54] | 12/24 |
| 8 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 8 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 8 | masked_copy | 1.37 [0.39, 2.73] | 0.78 [0.00, 1.95] | 1.17 [0.20, 2.54] | 12/24 |
| 16 | standard_preserve | 66.21 [61.52, 70.90] | 53.91 [49.61, 58.20] | 64.84 [60.94, 68.75] | 18/24 |
| 16 | standard_rewrite | 49.22 [44.92, 53.52] | 41.02 [37.30, 44.92] | 47.07 [43.16, 51.17] | 18/24 |
| 16 | bridge_preserve | 91.21 [87.89, 94.34] | 87.30 [83.59, 90.82] | 90.04 [85.94, 93.75] | 24/24 |
| 16 | bridge_rewrite | 93.95 [91.41, 96.29] | 89.45 [86.13, 92.38] | 93.36 [90.43, 96.09] | 24/24 |
| 16 | contrast_preserve | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |
| 16 | bridge_read_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 11/24 |
| 16 | bridge_write_blocked | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0/24 |
| 16 | protected_copy | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 100.00 [100.00, 100.00] | 24/24 |
| 16 | masked_copy | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 12/24 |

Prespecified secondary repair rescue versus pure contrast: **87.30 [83.59, 90.82] percentage points**.
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

Fresh independent histories and a byte-identical E038 numerical model; no earlier cases pooled. The joint primary and bridge-preserve durability are separate. Full confirmation requires both. Blocked variants are matched to preservation; this study does not qualify the rewrite variant under matched reading/writing ablations. All controls, receiver panels, pointwise secondary contrasts, body scores and changes from h1 are in summary.json. A finite sixteen-renewal result does not establish indefinite maintenance. Technical outcomes cannot decide scientific claims.
